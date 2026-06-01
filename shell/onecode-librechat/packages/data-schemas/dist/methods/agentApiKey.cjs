'use strict';

var index = require('../crypto/index.cjs');
var winston = require('../config/winston.cjs');

const API_KEY_PREFIX = 'sk-';
const API_KEY_LENGTH = 32;
function createAgentApiKeyMethods(mongoose) {
    async function generateApiKey() {
        const randomPart = await index.getRandomValues(API_KEY_LENGTH);
        const key = `${API_KEY_PREFIX}${randomPart}`;
        const keyHash = await index.hashToken(key);
        const keyPrefix = key.slice(0, 8);
        return { key, keyHash, keyPrefix };
    }
    async function createAgentApiKey(data) {
        try {
            const AgentApiKey = mongoose.models.AgentApiKey;
            const { key, keyHash, keyPrefix } = await generateApiKey();
            const apiKeyDoc = await AgentApiKey.create({
                userId: data.userId,
                name: data.name,
                keyHash,
                keyPrefix,
                expiresAt: data.expiresAt || undefined,
            });
            return {
                id: apiKeyDoc._id.toString(),
                name: apiKeyDoc.name,
                keyPrefix,
                key,
                createdAt: apiKeyDoc.createdAt,
                expiresAt: apiKeyDoc.expiresAt,
            };
        }
        catch (error) {
            winston.error('[createAgentApiKey] Error creating API key:', error);
            throw error;
        }
    }
    async function validateAgentApiKey(apiKey) {
        try {
            const AgentApiKey = mongoose.models.AgentApiKey;
            const keyHash = await index.hashToken(apiKey);
            const keyDoc = (await AgentApiKey.findOne({ keyHash }).lean());
            if (!keyDoc) {
                return null;
            }
            if (keyDoc.expiresAt && new Date(keyDoc.expiresAt) < new Date()) {
                return null;
            }
            await AgentApiKey.updateOne({ _id: keyDoc._id }, { $set: { lastUsedAt: new Date() } });
            return {
                userId: keyDoc.userId,
                keyId: keyDoc._id,
            };
        }
        catch (error) {
            winston.error('[validateAgentApiKey] Error validating API key:', error);
            return null;
        }
    }
    async function listAgentApiKeys(userId) {
        try {
            const AgentApiKey = mongoose.models.AgentApiKey;
            const keys = (await AgentApiKey.find({ userId })
                .sort({ createdAt: -1 })
                .lean());
            return keys.map((key) => ({
                id: key._id.toString(),
                name: key.name,
                keyPrefix: key.keyPrefix,
                lastUsedAt: key.lastUsedAt,
                expiresAt: key.expiresAt,
                createdAt: key.createdAt,
            }));
        }
        catch (error) {
            winston.error('[listAgentApiKeys] Error listing API keys:', error);
            throw error;
        }
    }
    async function deleteAgentApiKey(keyId, userId) {
        try {
            const AgentApiKey = mongoose.models.AgentApiKey;
            const result = await AgentApiKey.deleteOne({ _id: keyId, userId });
            return result.deletedCount > 0;
        }
        catch (error) {
            winston.error('[deleteAgentApiKey] Error deleting API key:', error);
            throw error;
        }
    }
    async function deleteAllAgentApiKeys(userId) {
        try {
            const AgentApiKey = mongoose.models.AgentApiKey;
            const result = await AgentApiKey.deleteMany({ userId });
            return result.deletedCount;
        }
        catch (error) {
            winston.error('[deleteAllAgentApiKeys] Error deleting all API keys:', error);
            throw error;
        }
    }
    async function getAgentApiKeyById(keyId, userId) {
        try {
            const AgentApiKey = mongoose.models.AgentApiKey;
            const keyDoc = (await AgentApiKey.findOne({
                _id: keyId,
                userId,
            }).lean());
            if (!keyDoc) {
                return null;
            }
            return {
                id: keyDoc._id.toString(),
                name: keyDoc.name,
                keyPrefix: keyDoc.keyPrefix,
                lastUsedAt: keyDoc.lastUsedAt,
                expiresAt: keyDoc.expiresAt,
                createdAt: keyDoc.createdAt,
            };
        }
        catch (error) {
            winston.error('[getAgentApiKeyById] Error getting API key:', error);
            throw error;
        }
    }
    return {
        createAgentApiKey,
        validateAgentApiKey,
        listAgentApiKeys,
        deleteAgentApiKey,
        deleteAllAgentApiKeys,
        getAgentApiKeyById,
    };
}

exports.createAgentApiKeyMethods = createAgentApiKeyMethods;
//# sourceMappingURL=agentApiKey.cjs.map
