import { RetentionMode } from 'librechat-data-provider';
import { createTempChatExpirationDate } from '../utils/tempChatRetention.es.js';
import { createFallbackRetentionDate, buildRetentionVisibilityFilter } from '../utils/retention.es.js';
import { tenantSafeBulkWrite } from '../utils/tenantBulkWrite.es.js';
import logger from '../config/winston.es.js';

function createConversationMethods(mongoose, messageMethods) {
    function getMessageMethods() {
        if (!messageMethods) {
            throw new Error('Message methods not injected into conversation methods');
        }
        return messageMethods;
    }
    function getVisibleConversationRetentionFilter() {
        return buildRetentionVisibilityFilter();
    }
    /**
     * Searches for a conversation by conversationId and returns a lean document with only conversationId and user.
     */
    async function searchConversation(conversationId) {
        try {
            const Conversation = mongoose.models.Conversation;
            return await Conversation.findOne({ conversationId }, 'conversationId user').lean();
        }
        catch (error) {
            logger.error('[searchConversation] Error searching conversation', error);
            throw new Error('Error searching conversation');
        }
    }
    /**
     * Retrieves a single conversation for a given user and conversation ID.
     */
    async function getConvo(user, conversationId) {
        try {
            const Conversation = mongoose.models.Conversation;
            return await Conversation.findOne({ user, conversationId }).lean();
        }
        catch (error) {
            logger.error('[getConvo] Error getting single conversation', error);
            throw new Error('Error getting single conversation');
        }
    }
    /**
     * Retrieves only the retention deadline for a conversation.
     */
    async function getConvoRetention(user, conversationId) {
        try {
            const Conversation = mongoose.models.Conversation;
            return await Conversation.findOne({ user, conversationId }, 'expiredAt').lean();
        }
        catch (error) {
            logger.error('[getConvoRetention] Error getting conversation retention fields', error);
            throw new Error('Error getting conversation retention fields');
        }
    }
    /**
     * Deletes conversations and messages with null or empty IDs.
     */
    async function deleteNullOrEmptyConversations() {
        try {
            const Conversation = mongoose.models.Conversation;
            const { deleteMessages } = getMessageMethods();
            const filter = {
                $or: [
                    { conversationId: null },
                    { conversationId: '' },
                    { conversationId: { $exists: false } },
                ],
            };
            const result = await Conversation.deleteMany(filter);
            const messageDeleteResult = await deleteMessages(filter);
            logger.info(`[deleteNullOrEmptyConversations] Deleted ${result.deletedCount} conversations and ${messageDeleteResult.deletedCount} messages`);
            return {
                conversations: result,
                messages: messageDeleteResult,
            };
        }
        catch (error) {
            logger.error('[deleteNullOrEmptyConversations] Error deleting conversations', error);
            throw new Error('Error deleting conversations with null or empty conversationId');
        }
    }
    /**
     * Searches for a conversation by conversationId and returns associated file ids.
     */
    async function getConvoFiles(conversationId) {
        var _a, _b;
        try {
            const Conversation = mongoose.models.Conversation;
            return ((_b = (_a = (await Conversation.findOne({ conversationId }, 'files').lean())) === null || _a === void 0 ? void 0 : _a.files) !== null && _b !== void 0 ? _b : []);
        }
        catch (error) {
            logger.error('[getConvoFiles] Error getting conversation files', error);
            throw new Error('Error getting conversation files');
        }
    }
    /**
     * Saves a conversation to the database.
     */
    async function saveConvo({ userId, isTemporary, interfaceConfig, }, { conversationId, newConversationId, ...convo }, metadata) {
        try {
            const Conversation = mongoose.models.Conversation;
            const { getMessages } = getMessageMethods();
            if (metadata === null || metadata === void 0 ? void 0 : metadata.context) {
                logger.debug(`[saveConvo] ${metadata.context}`);
            }
            const messages = await getMessages({ conversationId, user: userId }, '_id');
            const update = { ...convo, messages, user: userId };
            if (newConversationId) {
                update.conversationId = newConversationId;
            }
            if ((interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.retentionMode) === RetentionMode.ALL) {
                if (typeof isTemporary === 'boolean') {
                    update.isTemporary = isTemporary;
                }
                try {
                    update.expiredAt = createTempChatExpirationDate(interfaceConfig);
                }
                catch (err) {
                    logger.error('Error creating temporary chat expiration date:', err);
                    logger.info(`---\`saveConvo\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
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
                    logger.info(`---\`saveConvo\` context: ${metadata === null || metadata === void 0 ? void 0 : metadata.context}`);
                    update.expiredAt = createFallbackRetentionDate();
                }
            }
            else if (isTemporary === false) {
                update.isTemporary = false;
                update.expiredAt = null;
            }
            const createdAtOnInsert = (metadata === null || metadata === void 0 ? void 0 : metadata.createdAtOnInsert) instanceof Date &&
                !Number.isNaN(metadata.createdAtOnInsert.getTime())
                ? metadata.createdAtOnInsert
                : undefined;
            if (createdAtOnInsert) {
                update.updatedAt = new Date();
            }
            const updateOperation = { $set: update };
            if ((metadata === null || metadata === void 0 ? void 0 : metadata.unsetFields) && Object.keys(metadata.unsetFields).length > 0) {
                updateOperation.$unset = metadata.unsetFields;
            }
            if (createdAtOnInsert) {
                updateOperation.$setOnInsert = { createdAt: createdAtOnInsert };
            }
            const conversation = await Conversation.findOneAndUpdate({ conversationId, user: userId }, updateOperation, {
                new: true,
                upsert: (metadata === null || metadata === void 0 ? void 0 : metadata.noUpsert) !== true,
                ...(createdAtOnInsert ? { timestamps: false } : {}),
            });
            if (!conversation) {
                logger.debug('[saveConvo] Conversation not found, skipping update');
                return null;
            }
            if ((interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.retentionMode) === RetentionMode.ALL &&
                typeof isTemporary !== 'boolean' &&
                (conversation.isTemporary == null ||
                    (conversation.isTemporary === false && conversation.$isDefault('isTemporary')))) {
                await Conversation.updateOne({ _id: conversation._id, isTemporary: { $ne: false } }, { $set: { isTemporary: false } });
                conversation.isTemporary = false;
            }
            return conversation.toObject();
        }
        catch (error) {
            logger.error('[saveConvo] Error saving conversation', error);
            if (metadata === null || metadata === void 0 ? void 0 : metadata.context) {
                logger.info(`[saveConvo] ${metadata.context}`);
            }
            return { message: 'Error saving conversation' };
        }
    }
    /**
     * Saves multiple conversations in bulk.
     */
    async function bulkSaveConvos(conversations) {
        try {
            const Conversation = mongoose.models.Conversation;
            const bulkOps = conversations.map((convo) => ({
                updateOne: {
                    filter: {
                        conversationId: convo.conversationId,
                        user: convo.user,
                    },
                    update: convo,
                    upsert: true,
                    timestamps: false,
                },
            }));
            const result = await tenantSafeBulkWrite(Conversation, bulkOps);
            return result;
        }
        catch (error) {
            logger.error('[bulkSaveConvos] Error saving conversations in bulk', error);
            throw new Error('Failed to save conversations in bulk.');
        }
    }
    /**
     * Retrieves conversations using cursor-based pagination.
     */
    async function getConvosByCursor(user, { cursor, limit = 25, isArchived = false, tags, search, sortBy = 'updatedAt', sortDirection = 'desc', } = {}) {
        var _a;
        const Conversation = mongoose.models.Conversation;
        const filters = [{ user }];
        if (isArchived) {
            filters.push({ isArchived: true });
        }
        else {
            filters.push({
                $or: [{ isArchived: false }, { isArchived: { $exists: false } }],
            });
        }
        if (Array.isArray(tags) && tags.length > 0) {
            filters.push({ tags: { $in: tags } });
        }
        filters.push(getVisibleConversationRetentionFilter());
        if (search) {
            try {
                const meiliResults = await Conversation.meiliSearch(search, { filter: `user = "${user}"` });
                const matchingIds = Array.isArray(meiliResults.hits)
                    ? meiliResults.hits.map((result) => result.conversationId)
                    : [];
                if (!matchingIds.length) {
                    return { conversations: [], nextCursor: null };
                }
                filters.push({ conversationId: { $in: matchingIds } });
            }
            catch (error) {
                logger.error('[getConvosByCursor] Error during meiliSearch', error);
                throw new Error('Error during meiliSearch');
            }
        }
        const validSortFields = ['title', 'createdAt', 'updatedAt'];
        if (!validSortFields.includes(sortBy)) {
            throw new Error(`Invalid sortBy field: ${sortBy}. Must be one of ${validSortFields.join(', ')}`);
        }
        const finalSortBy = sortBy;
        const finalSortDirection = sortDirection === 'asc' ? 'asc' : 'desc';
        let cursorFilter = null;
        if (cursor) {
            try {
                const decoded = JSON.parse(Buffer.from(cursor, 'base64').toString());
                const { primary, secondary } = decoded;
                const primaryValue = finalSortBy === 'title' ? primary : new Date(primary);
                const secondaryValue = new Date(secondary);
                const op = finalSortDirection === 'asc' ? '$gt' : '$lt';
                cursorFilter = {
                    $or: [
                        { [finalSortBy]: { [op]: primaryValue } },
                        {
                            [finalSortBy]: primaryValue,
                            updatedAt: { [op]: secondaryValue },
                        },
                    ],
                };
            }
            catch {
                logger.warn('[getConvosByCursor] Invalid cursor format, starting from beginning');
            }
            if (cursorFilter) {
                filters.push(cursorFilter);
            }
        }
        const query = filters.length === 1 ? filters[0] : { $and: filters };
        try {
            const sortOrder = finalSortDirection === 'asc' ? 1 : -1;
            const sortObj = { [finalSortBy]: sortOrder };
            if (finalSortBy !== 'updatedAt') {
                sortObj.updatedAt = sortOrder;
            }
            const convos = await Conversation.find(query)
                .select('conversationId endpoint title createdAt updatedAt user model agent_id assistant_id spec iconURL')
                .sort(sortObj)
                .limit(limit + 1)
                .lean();
            let nextCursor = null;
            if (convos.length > limit) {
                convos.pop();
                const lastReturned = convos[convos.length - 1];
                let primaryValue = lastReturned.updatedAt;
                if (finalSortBy === 'title') {
                    primaryValue = lastReturned.title;
                }
                else if (finalSortBy === 'createdAt') {
                    primaryValue = lastReturned.createdAt;
                }
                const primaryStr = finalSortBy === 'title' ? primaryValue : new Date(primaryValue !== null && primaryValue !== void 0 ? primaryValue : 0).toISOString();
                const secondaryStr = new Date((_a = lastReturned.updatedAt) !== null && _a !== void 0 ? _a : 0).toISOString();
                const composite = { primary: primaryStr, secondary: secondaryStr };
                nextCursor = Buffer.from(JSON.stringify(composite)).toString('base64');
            }
            return { conversations: convos, nextCursor };
        }
        catch (error) {
            logger.error('[getConvosByCursor] Error getting conversations', error);
            throw new Error('Error getting conversations');
        }
    }
    /**
     * Fetches specific conversations by ID array with pagination.
     */
    async function getConvosQueried(user, convoIds, cursor = null, limit = 25) {
        try {
            const Conversation = mongoose.models.Conversation;
            if (!(convoIds === null || convoIds === void 0 ? void 0 : convoIds.length)) {
                return { conversations: [], nextCursor: null, convoMap: {} };
            }
            const conversationIds = convoIds.map((convo) => convo.conversationId);
            const results = await Conversation.find({
                user,
                conversationId: { $in: conversationIds },
                ...getVisibleConversationRetentionFilter(),
            }).lean();
            results.sort((a, b) => { var _a, _b; return new Date((_a = b.updatedAt) !== null && _a !== void 0 ? _a : 0).getTime() - new Date((_b = a.updatedAt) !== null && _b !== void 0 ? _b : 0).getTime(); });
            let filtered = results;
            if (cursor && cursor !== 'start') {
                const cursorDate = new Date(cursor);
                filtered = results.filter((convo) => { var _a; return new Date((_a = convo.updatedAt) !== null && _a !== void 0 ? _a : 0) < cursorDate; });
            }
            const limited = filtered.slice(0, limit + 1);
            let nextCursor = null;
            if (limited.length > limit) {
                limited.pop();
                nextCursor = limited[limited.length - 1].updatedAt.toISOString();
            }
            const convoMap = {};
            limited.forEach((convo) => {
                convoMap[convo.conversationId] = convo;
            });
            return { conversations: limited, nextCursor, convoMap };
        }
        catch (error) {
            logger.error('[getConvosQueried] Error getting conversations', error);
            throw new Error('Error fetching conversations');
        }
    }
    /**
     * Gets conversation title, returning 'New Chat' as default.
     */
    async function getConvoTitle(user, conversationId) {
        try {
            const convo = await getConvo(user, conversationId);
            if (convo && !convo.title) {
                return null;
            }
            else {
                return (convo === null || convo === void 0 ? void 0 : convo.title) || 'New Chat';
            }
        }
        catch (error) {
            logger.error('[getConvoTitle] Error getting conversation title', error);
            throw new Error('Error getting conversation title');
        }
    }
    /**
     * Deletes conversations and their associated messages for a given user and filter.
     */
    async function deleteConvos(user, filter) {
        try {
            const Conversation = mongoose.models.Conversation;
            const { deleteMessages } = getMessageMethods();
            const userFilter = { ...filter, user };
            const conversations = await Conversation.find(userFilter).select('conversationId');
            const conversationIds = conversations.map((c) => c.conversationId);
            if (!conversationIds.length) {
                throw new Error('Conversation not found or already deleted.');
            }
            const deleteConvoResult = await Conversation.deleteMany(userFilter);
            const deleteMessagesResult = await deleteMessages({
                conversationId: { $in: conversationIds },
                user,
            });
            return { ...deleteConvoResult, messages: deleteMessagesResult };
        }
        catch (error) {
            logger.error('[deleteConvos] Error deleting conversations and messages', error);
            throw error;
        }
    }
    return {
        getConvoFiles,
        searchConversation,
        deleteNullOrEmptyConversations,
        saveConvo,
        bulkSaveConvos,
        getConvosByCursor,
        getConvosQueried,
        getConvo,
        getConvoRetention,
        getConvoTitle,
        deleteConvos,
    };
}

export { createConversationMethods };
//# sourceMappingURL=conversation.es.js.map
