import logger from '../config/winston.es.js';

const CANCEL_RATE = 1.15;
/**
 * Checks if the connected MongoDB deployment supports transactions
 * This requires a MongoDB replica set configuration
 *
 * @returns True if transactions are supported, false otherwise
 */
const supportsTransactions = async (mongoose) => {
    var _a;
    try {
        const session = await mongoose.startSession();
        try {
            session.startTransaction();
            await ((_a = mongoose.connection.db) === null || _a === void 0 ? void 0 : _a.collection('__transaction_test__').findOne({}, { session }));
            await session.commitTransaction();
            logger.debug('MongoDB transactions are supported');
            return true;
        }
        catch (transactionError) {
            try {
                await session.abortTransaction();
            }
            catch (transactionError) {
                /** best-effort abort */
                logger.error(`[supportsTransactions] Error aborting transaction:`, transactionError);
            }
            logger.debug('MongoDB transactions not supported (transaction error):', (transactionError === null || transactionError === void 0 ? void 0 : transactionError.message) || 'Unknown error');
            return false;
        }
        finally {
            await session.endSession();
        }
    }
    catch (error) {
        logger.debug('MongoDB transactions not supported (session error):', (error === null || error === void 0 ? void 0 : error.message) || 'Unknown error');
        return false;
    }
};
/**
 * Gets whether the current MongoDB deployment supports transactions
 * Caches the result for performance
 *
 * @returns True if transactions are supported, false otherwise
 */
const getTransactionSupport = async (mongoose, transactionSupportCache) => {
    let transactionsSupported = false;
    if (transactionSupportCache === null) {
        transactionsSupported = await supportsTransactions(mongoose);
    }
    return transactionsSupported;
};

export { CANCEL_RATE, getTransactionSupport, supportsTransactions };
//# sourceMappingURL=transactions.es.js.map
