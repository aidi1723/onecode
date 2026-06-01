'use strict';

var winston = require('../config/winston.cjs');

// Factory function that takes mongoose instance and returns the methods
function createTokenMethods(mongoose) {
    /**
     * Creates a new Token instance.
     */
    async function createToken(tokenData) {
        try {
            const Token = mongoose.models.Token;
            const currentTime = new Date();
            const expiresAt = new Date(currentTime.getTime() + tokenData.expiresIn * 1000);
            const newTokenData = {
                ...tokenData,
                createdAt: currentTime,
                expiresAt,
            };
            return await Token.create(newTokenData);
        }
        catch (error) {
            winston.debug('An error occurred while creating token:', error);
            throw error;
        }
    }
    /**
     * Updates a Token document that matches the provided query.
     */
    async function updateToken(query, updateData) {
        try {
            const Token = mongoose.models.Token;
            const dataToUpdate = { ...updateData };
            if ((updateData === null || updateData === void 0 ? void 0 : updateData.expiresIn) !== undefined) {
                dataToUpdate.expiresAt = new Date(Date.now() + updateData.expiresIn * 1000);
            }
            return await Token.findOneAndUpdate(query, dataToUpdate, { new: true });
        }
        catch (error) {
            winston.debug('An error occurred while updating token:', error);
            throw error;
        }
    }
    /** Deletes all Token documents matching every provided field (AND semantics). */
    async function deleteTokens(query) {
        try {
            const Token = mongoose.models.Token;
            const conditions = [];
            if (query.userId !== undefined) {
                conditions.push({ userId: query.userId });
            }
            if (query.token !== undefined) {
                conditions.push({ token: query.token });
            }
            if (query.email !== undefined) {
                conditions.push({ email: query.email.trim().toLowerCase() });
            }
            if (query.type !== undefined) {
                conditions.push({ type: query.type });
            }
            if (query.identifier !== undefined) {
                conditions.push({ identifier: query.identifier });
            }
            if (conditions.length === 0) {
                throw new Error('At least one query parameter must be provided');
            }
            return await Token.deleteMany({
                $and: conditions,
            });
        }
        catch (error) {
            winston.debug('An error occurred while deleting tokens:', error);
            throw error;
        }
    }
    /**
     * Finds a Token document that matches the provided query.
     * Email is automatically normalized to lowercase for case-insensitive matching.
     */
    async function findToken(query, options) {
        try {
            const Token = mongoose.models.Token;
            const conditions = [];
            if (query.userId) {
                conditions.push({ userId: query.userId });
            }
            if (query.token) {
                conditions.push({ token: query.token });
            }
            if (query.email) {
                conditions.push({ email: query.email.trim().toLowerCase() });
            }
            if (query.type) {
                conditions.push({ type: query.type });
            }
            if (query.identifier) {
                conditions.push({ identifier: query.identifier });
            }
            const token = await Token.findOne({ $and: conditions }, null, options).lean();
            return token;
        }
        catch (error) {
            winston.debug('An error occurred while finding token:', error);
            throw error;
        }
    }
    // Return all methods
    return {
        findToken,
        createToken,
        updateToken,
        deleteTokens,
    };
}

exports.createTokenMethods = createTokenMethods;
//# sourceMappingURL=token.cjs.map
