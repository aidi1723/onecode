'use strict';

var winston = require('../config/winston.cjs');

const cancelRate = 1.15;
function createTransactionMethods(mongoose, txMethods) {
    /** Calculate and set the tokenValue for a transaction */
    function calculateTokenValue(txn) {
        var _a, _b, _c;
        const { valueKey, tokenType, model, endpointTokenConfig, inputTokenCount } = txn;
        const multiplier = Math.abs(txMethods.getMultiplier({
            valueKey,
            tokenType: tokenType,
            model,
            endpointTokenConfig: endpointTokenConfig !== null && endpointTokenConfig !== void 0 ? endpointTokenConfig : undefined,
            inputTokenCount,
        }));
        txn.rate = multiplier;
        txn.tokenValue = ((_a = txn.rawAmount) !== null && _a !== void 0 ? _a : 0) * multiplier;
        if (txn.context && txn.tokenType === 'completion' && txn.context === 'incomplete') {
            txn.tokenValue = Math.ceil(((_b = txn.tokenValue) !== null && _b !== void 0 ? _b : 0) * cancelRate);
            txn.rate = ((_c = txn.rate) !== null && _c !== void 0 ? _c : 0) * cancelRate;
        }
    }
    /** Calculate token value for structured tokens */
    function calculateStructuredTokenValue(txn) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p, _q;
        if (!txn.tokenType) {
            txn.tokenValue = txn.rawAmount;
            return;
        }
        const { model, endpointTokenConfig, inputTokenCount } = txn;
        const etConfig = endpointTokenConfig !== null && endpointTokenConfig !== void 0 ? endpointTokenConfig : undefined;
        if (txn.tokenType === 'prompt') {
            const inputMultiplier = txMethods.getMultiplier({
                tokenType: 'prompt',
                model,
                endpointTokenConfig: etConfig,
                inputTokenCount,
            });
            const writeMultiplier = (_a = txMethods.getCacheMultiplier({
                cacheType: 'write',
                model,
                endpointTokenConfig: etConfig,
            })) !== null && _a !== void 0 ? _a : inputMultiplier;
            const readMultiplier = (_b = txMethods.getCacheMultiplier({ cacheType: 'read', model, endpointTokenConfig: etConfig })) !== null && _b !== void 0 ? _b : inputMultiplier;
            txn.rateDetail = {
                input: inputMultiplier,
                write: writeMultiplier,
                read: readMultiplier,
            };
            const totalPromptTokens = Math.abs((_c = txn.inputTokens) !== null && _c !== void 0 ? _c : 0) +
                Math.abs((_d = txn.writeTokens) !== null && _d !== void 0 ? _d : 0) +
                Math.abs((_e = txn.readTokens) !== null && _e !== void 0 ? _e : 0);
            if (totalPromptTokens > 0) {
                txn.rate =
                    (Math.abs(inputMultiplier * ((_f = txn.inputTokens) !== null && _f !== void 0 ? _f : 0)) +
                        Math.abs(writeMultiplier * ((_g = txn.writeTokens) !== null && _g !== void 0 ? _g : 0)) +
                        Math.abs(readMultiplier * ((_h = txn.readTokens) !== null && _h !== void 0 ? _h : 0))) /
                        totalPromptTokens;
            }
            else {
                txn.rate = Math.abs(inputMultiplier);
            }
            txn.tokenValue = -(Math.abs((_j = txn.inputTokens) !== null && _j !== void 0 ? _j : 0) * inputMultiplier +
                Math.abs((_k = txn.writeTokens) !== null && _k !== void 0 ? _k : 0) * writeMultiplier +
                Math.abs((_l = txn.readTokens) !== null && _l !== void 0 ? _l : 0) * readMultiplier);
            txn.rawAmount = -totalPromptTokens;
        }
        else if (txn.tokenType === 'completion') {
            const multiplier = txMethods.getMultiplier({
                tokenType: txn.tokenType,
                model,
                endpointTokenConfig: etConfig,
                inputTokenCount,
            });
            txn.rate = Math.abs(multiplier);
            txn.tokenValue = -Math.abs((_m = txn.rawAmount) !== null && _m !== void 0 ? _m : 0) * multiplier;
            txn.rawAmount = -Math.abs((_o = txn.rawAmount) !== null && _o !== void 0 ? _o : 0);
        }
        if (txn.context && txn.tokenType === 'completion' && txn.context === 'incomplete') {
            txn.tokenValue = Math.ceil(((_p = txn.tokenValue) !== null && _p !== void 0 ? _p : 0) * cancelRate);
            txn.rate = ((_q = txn.rate) !== null && _q !== void 0 ? _q : 0) * cancelRate;
            if (txn.rateDetail) {
                txn.rateDetail = Object.fromEntries(Object.entries(txn.rateDetail).map(([k, v]) => [k, v * cancelRate]));
            }
        }
    }
    /**
     * Updates a user's token balance using optimistic concurrency control.
     * Always returns an IBalance or throws after exhausting retries.
     */
    async function updateBalance({ user, incrementValue, setValues, }) {
        const Balance = mongoose.models.Balance;
        const maxRetries = 10;
        let delay = 50;
        let lastError = null;
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            let currentBalanceDoc;
            try {
                currentBalanceDoc = await Balance.findOne({ user }).lean();
                const currentCredits = currentBalanceDoc ? currentBalanceDoc.tokenCredits : 0;
                const potentialNewCredits = currentCredits + incrementValue;
                const newCredits = Math.max(0, potentialNewCredits);
                const updatePayload = {
                    $set: {
                        tokenCredits: newCredits,
                        ...(setValues !== null && setValues !== void 0 ? setValues : {}),
                    },
                };
                let updatedBalance = null;
                if (currentBalanceDoc) {
                    updatedBalance = await Balance.findOneAndUpdate({ user, tokenCredits: currentCredits }, updatePayload, { new: true }).lean();
                    if (updatedBalance) {
                        return updatedBalance;
                    }
                    lastError = new Error(`Concurrency conflict for user ${user} on attempt ${attempt}.`);
                }
                else {
                    try {
                        updatedBalance = await Balance.findOneAndUpdate({ user }, updatePayload, {
                            upsert: true,
                            new: true,
                        }).lean();
                        if (updatedBalance) {
                            return updatedBalance;
                        }
                        lastError = new Error(`Upsert race condition suspected for user ${user} on attempt ${attempt}.`);
                    }
                    catch (error) {
                        if (error instanceof Error &&
                            'code' in error &&
                            error.code === 11000) {
                            lastError = error;
                        }
                        else {
                            throw error;
                        }
                    }
                }
            }
            catch (error) {
                winston.error(`[updateBalance] Error during attempt ${attempt} for user ${user}:`, error);
                lastError = error instanceof Error ? error : new Error(String(error));
            }
            if (attempt < maxRetries) {
                const jitter = Math.random() * delay * 0.5;
                await new Promise((resolve) => setTimeout(resolve, delay + jitter));
                delay = Math.min(delay * 2, 2000);
            }
        }
        winston.error(`[updateBalance] Failed to update balance for user ${user} after ${maxRetries} attempts.`);
        throw (lastError !== null && lastError !== void 0 ? lastError : new Error(`Failed to update balance for user ${user} after maximum retries due to persistent conflicts.`));
    }
    /**
     * Creates an auto-refill transaction that also updates balance.
     */
    async function createAutoRefillTransaction(txData) {
        var _a;
        if (txData.rawAmount != null && isNaN(txData.rawAmount)) {
            return;
        }
        const Transaction = mongoose.models.Transaction;
        const transaction = new Transaction(txData);
        transaction.endpointTokenConfig = txData.endpointTokenConfig;
        transaction.inputTokenCount = txData.inputTokenCount;
        calculateTokenValue(transaction);
        await transaction.save();
        const balanceResponse = await updateBalance({
            user: transaction.user,
            incrementValue: (_a = txData.rawAmount) !== null && _a !== void 0 ? _a : 0,
            setValues: { lastRefill: new Date() },
        });
        const result = {
            rate: transaction.rate,
            user: transaction.user.toString(),
            balance: balanceResponse.tokenCredits,
            transaction,
        };
        winston.debug('[Balance.check] Auto-refill performed', result);
        return result;
    }
    /**
     * Creates a transaction and updates the balance.
     */
    async function createTransaction(_txData) {
        const { balance, transactions, ...txData } = _txData;
        if (txData.rawAmount != null && isNaN(txData.rawAmount)) {
            return;
        }
        if ((transactions === null || transactions === void 0 ? void 0 : transactions.enabled) === false) {
            return;
        }
        const Transaction = mongoose.models.Transaction;
        const transaction = new Transaction(txData);
        transaction.endpointTokenConfig = txData.endpointTokenConfig;
        transaction.inputTokenCount = txData.inputTokenCount;
        calculateTokenValue(transaction);
        await transaction.save();
        if (!(balance === null || balance === void 0 ? void 0 : balance.enabled)) {
            return;
        }
        const incrementValue = transaction.tokenValue;
        const balanceResponse = await updateBalance({
            user: transaction.user,
            incrementValue,
        });
        return {
            rate: transaction.rate,
            user: transaction.user.toString(),
            balance: balanceResponse.tokenCredits,
            [transaction.tokenType]: incrementValue,
        };
    }
    /**
     * Creates a structured transaction and updates the balance.
     */
    async function createStructuredTransaction(_txData) {
        const { balance, transactions, ...txData } = _txData;
        if ((transactions === null || transactions === void 0 ? void 0 : transactions.enabled) === false) {
            return;
        }
        const Transaction = mongoose.models.Transaction;
        const transaction = new Transaction(txData);
        transaction.endpointTokenConfig = txData.endpointTokenConfig;
        transaction.inputTokenCount = txData.inputTokenCount;
        calculateStructuredTokenValue(transaction);
        await transaction.save();
        if (!(balance === null || balance === void 0 ? void 0 : balance.enabled)) {
            return;
        }
        const incrementValue = transaction.tokenValue;
        const balanceResponse = await updateBalance({
            user: transaction.user,
            incrementValue,
        });
        return {
            rate: transaction.rate,
            user: transaction.user.toString(),
            balance: balanceResponse.tokenCredits,
            [transaction.tokenType]: incrementValue,
        };
    }
    /**
     * Queries and retrieves transactions based on a given filter.
     */
    async function getTransactions(filter) {
        try {
            const Transaction = mongoose.models.Transaction;
            return await Transaction.find(filter).lean();
        }
        catch (error) {
            winston.error('Error querying transactions:', error);
            throw error;
        }
    }
    /** Retrieves a user's balance record. */
    async function findBalanceByUser(user) {
        const Balance = mongoose.models.Balance;
        return Balance.findOne({ user }).lean();
    }
    /** Upserts balance fields for a user. */
    async function upsertBalanceFields(user, fields) {
        const Balance = mongoose.models.Balance;
        return Balance.findOneAndUpdate({ user }, { $set: fields }, { upsert: true, new: true }).lean();
    }
    /** Deletes transactions matching a filter. */
    async function deleteTransactions(filter) {
        const Transaction = mongoose.models.Transaction;
        return Transaction.deleteMany(filter);
    }
    /** Deletes balance records matching a filter. */
    async function deleteBalances(filter) {
        const Balance = mongoose.models.Balance;
        return Balance.deleteMany(filter);
    }
    async function bulkInsertTransactions(docs) {
        if (!docs.length) {
            return;
        }
        try {
            const Transaction = mongoose.models.Transaction;
            await Transaction.insertMany(docs);
        }
        catch (error) {
            winston.error('[bulkInsertTransactions] Error inserting transaction docs:', error);
            throw error;
        }
    }
    return {
        updateBalance,
        bulkInsertTransactions,
        findBalanceByUser,
        upsertBalanceFields,
        getTransactions,
        deleteTransactions,
        deleteBalances,
        createTransaction,
        createAutoRefillTransaction,
        createStructuredTransaction,
    };
}

exports.createTransactionMethods = createTransactionMethods;
//# sourceMappingURL=transaction.cjs.map
