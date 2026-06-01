import { RetentionMode } from 'librechat-data-provider';
import logger from '../config/winston.es.js';
import { createTempChatExpirationDate } from '../utils/tempChatRetention.es.js';
import { createFallbackRetentionDate } from '../utils/retention.es.js';
import { tenantSafeBulkWrite } from '../utils/tenantBulkWrite.es.js';

/** Simple UUID v4 regex to replace zod validation */
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function createMessageMethods(mongoose) {
    /**
     * Saves a message in the database.
     */
    async function saveMessage({ userId, isTemporary, interfaceConfig, }, params, metadata) {
        var _a;
        if (!userId) {
            throw new Error('User not authenticated');
        }
        const conversationId = params.conversationId;
        if (!conversationId || !UUID_REGEX.test(conversationId)) {
            logger.warn(`Invalid conversation ID: ${conversationId}`);
            logger.info(`---\`saveMessage\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
            logger.info(`---Invalid conversation ID Params: ${JSON.stringify(params, null, 2)}`);
            return;
        }
        try {
            const Message = mongoose.models.Message;
            const update = {
                ...params,
                user: userId,
                messageId: params.newMessageId || params.messageId,
            };
            if ((interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.retentionMode) === RetentionMode.ALL) {
                if (typeof isTemporary === 'boolean') {
                    update.isTemporary = isTemporary;
                }
                try {
                    update.expiredAt = createTempChatExpirationDate(interfaceConfig);
                }
                catch (err) {
                    logger.error('Error creating temporary chat expiration date:', err);
                    logger.info(`---\`saveMessage\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
                    update.expiredAt = createFallbackRetentionDate();
                }
            }
            else if (isTemporary === true) {
                update.isTemporary = true;
                try {
                    update.expiredAt = createTempChatExpirationDate(interfaceConfig);
                }
                catch (err) {
                    logger.error('Error creating temporary chat expiration date:', err);
                    logger.info(`---\`saveMessage\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
                    update.expiredAt = createFallbackRetentionDate();
                }
            }
            else if (isTemporary === false) {
                update.isTemporary = false;
                update.expiredAt = null;
            }
            if (update.tokenCount != null && isNaN(update.tokenCount)) {
                logger.warn(`Resetting invalid \`tokenCount\` for message \`${params.messageId}\`: ${update.tokenCount}`);
                logger.info(`---\`saveMessage\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
                update.tokenCount = 0;
            }
            const message = await Message.findOneAndUpdate({ messageId: params.messageId, user: userId }, update, { upsert: true, new: true });
            if ((interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.retentionMode) === RetentionMode.ALL &&
                typeof isTemporary !== 'boolean' &&
                (message.isTemporary == null ||
                    (message.isTemporary === false && message.$isDefault('isTemporary')))) {
                await Message.updateOne({ _id: message._id, isTemporary: { $ne: false } }, { $set: { isTemporary: false } });
                message.isTemporary = false;
            }
            return message.toObject();
        }
        catch (err) {
            logger.error('Error saving message:', err);
            logger.info(`---\`saveMessage\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
            const mongoErr = err;
            if (mongoErr.code === 11000 && ((_a = mongoErr.message) === null || _a === void 0 ? void 0 : _a.includes('duplicate key error'))) {
                logger.warn(`Duplicate messageId detected: ${params.messageId}. Continuing execution.`);
                try {
                    const Message = mongoose.models.Message;
                    const existingMessage = await Message.findOne({
                        messageId: params.messageId,
                        user: userId,
                    });
                    if (existingMessage) {
                        return existingMessage.toObject();
                    }
                    return undefined;
                }
                catch (findError) {
                    logger.warn(`Could not retrieve existing message with ID ${params.messageId}: ${findError.message}`);
                    return undefined;
                }
            }
            throw err;
        }
    }
    /**
     * Saves multiple messages in bulk.
     */
    async function bulkSaveMessages(messages, overrideTimestamp = false) {
        try {
            const Message = mongoose.models.Message;
            const bulkOps = messages.map((message) => ({
                updateOne: {
                    filter: { messageId: message.messageId },
                    update: message,
                    timestamps: !overrideTimestamp,
                    upsert: true,
                },
            }));
            const result = await tenantSafeBulkWrite(Message, bulkOps);
            return result;
        }
        catch (err) {
            logger.error('Error saving messages in bulk:', err);
            throw err;
        }
    }
    /**
     * Records a message in the database (no UUID validation).
     */
    async function recordMessage({ user, endpoint, messageId, conversationId, parentMessageId, ...rest }) {
        try {
            const Message = mongoose.models.Message;
            const message = {
                user,
                endpoint,
                messageId,
                conversationId,
                parentMessageId,
                ...rest,
            };
            return await Message.findOneAndUpdate({ user, messageId }, message, {
                upsert: true,
                new: true,
            });
        }
        catch (err) {
            logger.error('Error recording message:', err);
            throw err;
        }
    }
    /**
     * Updates the text of a message.
     */
    async function updateMessageText(userId, { messageId, text }) {
        try {
            const Message = mongoose.models.Message;
            await Message.updateOne({ messageId, user: userId }, { text });
        }
        catch (err) {
            logger.error('Error updating message text:', err);
            throw err;
        }
    }
    /**
     * Updates a message and returns sanitized fields.
     */
    async function updateMessage(userId, message, metadata) {
        try {
            const Message = mongoose.models.Message;
            const { messageId, ...update } = message;
            const updatedMessage = await Message.findOneAndUpdate({ messageId, user: userId }, update, {
                new: true,
            });
            if (!updatedMessage) {
                throw new Error('Message not found or user not authorized.');
            }
            return {
                messageId: updatedMessage.messageId,
                conversationId: updatedMessage.conversationId,
                parentMessageId: updatedMessage.parentMessageId,
                sender: updatedMessage.sender,
                text: updatedMessage.text,
                isCreatedByUser: updatedMessage.isCreatedByUser,
                tokenCount: updatedMessage.tokenCount,
                feedback: updatedMessage.feedback,
            };
        }
        catch (err) {
            logger.error('Error updating message:', err);
            if (metadata === null || metadata === void 0 ? void 0 : metadata.context) {
                logger.info(`---\`updateMessage\` context: ${metadata.context}`);
            }
            throw err;
        }
    }
    /**
     * Deletes messages in a conversation since a specific message.
     */
    async function deleteMessagesSince(userId, { messageId, conversationId }) {
        try {
            const Message = mongoose.models.Message;
            const message = await Message.findOne({ messageId, user: userId }).lean();
            if (message) {
                const query = Message.find({ conversationId, user: userId });
                return await query.deleteMany({
                    createdAt: { $gt: message.createdAt },
                });
            }
            return undefined;
        }
        catch (err) {
            logger.error('Error deleting messages:', err);
            throw err;
        }
    }
    /**
     * Retrieves messages from the database.
     */
    async function getMessages(filter, select) {
        try {
            const Message = mongoose.models.Message;
            if (select) {
                return await Message.find(filter).select(select).sort({ createdAt: 1 }).lean();
            }
            return await Message.find(filter).sort({ createdAt: 1 }).lean();
        }
        catch (err) {
            logger.error('Error getting messages:', err);
            throw err;
        }
    }
    /**
     * Retrieves a single message from the database.
     */
    async function getMessage({ user, messageId }) {
        try {
            const Message = mongoose.models.Message;
            return await Message.findOne({ user, messageId }).lean();
        }
        catch (err) {
            logger.error('Error getting message:', err);
            throw err;
        }
    }
    /**
     * Deletes messages from the database.
     */
    async function deleteMessages(filter) {
        try {
            const Message = mongoose.models.Message;
            return await Message.deleteMany(filter);
        }
        catch (err) {
            logger.error('Error deleting messages:', err);
            throw err;
        }
    }
    /**
     * Retrieves paginated messages with custom sorting and cursor support.
     */
    async function getMessagesByCursor(filter, options = {}) {
        const Message = mongoose.models.Message;
        const { sortField = 'createdAt', sortOrder = -1, limit = 25, cursor } = options;
        const queryFilter = { ...filter };
        if (cursor) {
            queryFilter[sortField] = sortOrder === 1 ? { $gt: cursor } : { $lt: cursor };
        }
        const messages = await Message.find(queryFilter)
            .sort({ [sortField]: sortOrder })
            .limit(limit + 1)
            .lean();
        let nextCursor = null;
        if (messages.length > limit) {
            messages.pop();
            const last = messages[messages.length - 1];
            const cursorValue = sortField === 'createdAt' ? last.createdAt : last[sortField];
            nextCursor = String(cursorValue !== null && cursorValue !== void 0 ? cursorValue : '');
        }
        return { messages, nextCursor };
    }
    /**
     * Performs a MeiliSearch query on the Message collection.
     * Requires the meilisearch plugin to be registered on the Message model.
     */
    async function searchMessages(query, searchOptions, hydrate) {
        const Message = mongoose.models.Message;
        if (typeof Message.meiliSearch !== 'function') {
            throw new Error('MeiliSearch plugin not registered on Message model');
        }
        return Message.meiliSearch(query, searchOptions, hydrate);
    }
    return {
        saveMessage,
        bulkSaveMessages,
        recordMessage,
        updateMessageText,
        updateMessage,
        deleteMessagesSince,
        getMessages,
        getMessage,
        getMessagesByCursor,
        searchMessages,
        deleteMessages,
    };
}

export { createMessageMethods };
//# sourceMappingURL=message.es.js.map
