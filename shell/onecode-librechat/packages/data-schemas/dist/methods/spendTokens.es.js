import logger from '../config/winston.es.js';

function createSpendTokensMethods(_mongoose, transactionMethods) {
    /**
     * Creates up to two transactions to record the spending of tokens.
     */
    async function spendTokens(txData, tokenUsage) {
        var _a;
        const { promptTokens, completionTokens } = tokenUsage;
        logger.debug(`[spendTokens] conversationId: ${txData.conversationId}${(txData === null || txData === void 0 ? void 0 : txData.context) ? ` | Context: ${txData === null || txData === void 0 ? void 0 : txData.context}` : ''} | Token usage: `, { promptTokens, completionTokens });
        let prompt, completion;
        const normalizedPromptTokens = Math.max(promptTokens !== null && promptTokens !== void 0 ? promptTokens : 0, 0);
        try {
            if (promptTokens !== undefined) {
                prompt = await transactionMethods.createTransaction({
                    ...txData,
                    tokenType: 'prompt',
                    rawAmount: promptTokens === 0 ? 0 : -normalizedPromptTokens,
                    inputTokenCount: normalizedPromptTokens,
                });
            }
            if (completionTokens !== undefined) {
                completion = await transactionMethods.createTransaction({
                    ...txData,
                    tokenType: 'completion',
                    rawAmount: completionTokens === 0 ? 0 : -Math.max(completionTokens, 0),
                    inputTokenCount: normalizedPromptTokens,
                });
            }
            if (prompt || completion) {
                logger.debug('[spendTokens] Transaction data record against balance:', {
                    user: txData.user,
                    prompt: prompt === null || prompt === void 0 ? void 0 : prompt.prompt,
                    promptRate: prompt === null || prompt === void 0 ? void 0 : prompt.rate,
                    completion: completion === null || completion === void 0 ? void 0 : completion.completion,
                    completionRate: completion === null || completion === void 0 ? void 0 : completion.rate,
                    balance: (_a = completion === null || completion === void 0 ? void 0 : completion.balance) !== null && _a !== void 0 ? _a : prompt === null || prompt === void 0 ? void 0 : prompt.balance,
                });
            }
            else {
                logger.debug('[spendTokens] No transactions incurred against balance');
            }
        }
        catch (err) {
            logger.error('[spendTokens]', err);
        }
    }
    /**
     * Creates transactions to record the spending of structured tokens.
     */
    async function spendStructuredTokens(txData, tokenUsage) {
        var _a, _b, _c, _d, _e, _f, _g;
        const { promptTokens, completionTokens } = tokenUsage;
        logger.debug(`[spendStructuredTokens] conversationId: ${txData.conversationId}${(txData === null || txData === void 0 ? void 0 : txData.context) ? ` | Context: ${txData === null || txData === void 0 ? void 0 : txData.context}` : ''} | Token usage: `, { promptTokens, completionTokens });
        let prompt, completion;
        try {
            if (promptTokens) {
                const input = Math.max((_a = promptTokens.input) !== null && _a !== void 0 ? _a : 0, 0);
                const write = Math.max((_b = promptTokens.write) !== null && _b !== void 0 ? _b : 0, 0);
                const read = Math.max((_c = promptTokens.read) !== null && _c !== void 0 ? _c : 0, 0);
                const totalInputTokens = input + write + read;
                prompt = await transactionMethods.createStructuredTransaction({
                    ...txData,
                    tokenType: 'prompt',
                    inputTokens: -input,
                    writeTokens: -write,
                    readTokens: -read,
                    inputTokenCount: totalInputTokens,
                });
            }
            if (completionTokens) {
                const totalInputTokens = promptTokens
                    ? Math.max((_d = promptTokens.input) !== null && _d !== void 0 ? _d : 0, 0) +
                        Math.max((_e = promptTokens.write) !== null && _e !== void 0 ? _e : 0, 0) +
                        Math.max((_f = promptTokens.read) !== null && _f !== void 0 ? _f : 0, 0)
                    : undefined;
                completion = await transactionMethods.createTransaction({
                    ...txData,
                    tokenType: 'completion',
                    rawAmount: -Math.max(completionTokens, 0),
                    inputTokenCount: totalInputTokens,
                });
            }
            if (prompt || completion) {
                logger.debug('[spendStructuredTokens] Transaction data record against balance:', {
                    user: txData.user,
                    prompt: prompt === null || prompt === void 0 ? void 0 : prompt.prompt,
                    promptRate: prompt === null || prompt === void 0 ? void 0 : prompt.rate,
                    completion: completion === null || completion === void 0 ? void 0 : completion.completion,
                    completionRate: completion === null || completion === void 0 ? void 0 : completion.rate,
                    balance: (_g = completion === null || completion === void 0 ? void 0 : completion.balance) !== null && _g !== void 0 ? _g : prompt === null || prompt === void 0 ? void 0 : prompt.balance,
                });
            }
            else {
                logger.debug('[spendStructuredTokens] No transactions incurred against balance');
            }
        }
        catch (err) {
            logger.error('[spendStructuredTokens]', err);
        }
        return { prompt, completion };
    }
    return { spendTokens, spendStructuredTokens };
}

export { createSpendTokensMethods };
//# sourceMappingURL=spendTokens.es.js.map
