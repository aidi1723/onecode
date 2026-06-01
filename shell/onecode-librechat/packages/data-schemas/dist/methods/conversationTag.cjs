'use strict';

var tenantBulkWrite = require('../utils/tenantBulkWrite.cjs');
var winston = require('../config/winston.cjs');

function createConversationTagMethods(mongoose) {
    /**
     * Retrieves all conversation tags for a user.
     */
    async function getConversationTags(user) {
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            return await ConversationTag.find({ user }).sort({ position: 1 }).lean();
        }
        catch (error) {
            winston.error('[getConversationTags] Error getting conversation tags', error);
            throw new Error('Error getting conversation tags');
        }
    }
    /**
     * Creates a new conversation tag.
     */
    async function createConversationTag(user, data) {
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            const Conversation = mongoose.models.Conversation;
            const { tag, description, addToConversation, conversationId } = data;
            const existingTag = await ConversationTag.findOne({ user, tag }).lean();
            if (existingTag) {
                return existingTag;
            }
            const maxPosition = await ConversationTag.findOne({ user }).sort('-position').lean();
            const position = ((maxPosition === null || maxPosition === void 0 ? void 0 : maxPosition.position) || 0) + 1;
            const newTag = await ConversationTag.findOneAndUpdate({ tag, user }, {
                tag,
                user,
                count: addToConversation ? 1 : 0,
                position,
                description,
                $setOnInsert: { createdAt: new Date() },
            }, {
                new: true,
                upsert: true,
                lean: true,
            });
            if (addToConversation && conversationId) {
                await Conversation.findOneAndUpdate({ user, conversationId }, { $addToSet: { tags: tag } }, { new: true });
            }
            return newTag;
        }
        catch (error) {
            winston.error('[createConversationTag] Error creating conversation tag', error);
            throw new Error('Error creating conversation tag');
        }
    }
    /**
     * Adjusts positions of tags when a tag's position is changed.
     */
    async function adjustPositions(user, oldPosition, newPosition) {
        if (oldPosition === newPosition) {
            return;
        }
        const ConversationTag = mongoose.models.ConversationTag;
        const update = oldPosition < newPosition ? { $inc: { position: -1 } } : { $inc: { position: 1 } };
        const position = oldPosition < newPosition
            ? {
                $gt: Math.min(oldPosition, newPosition),
                $lte: Math.max(oldPosition, newPosition),
            }
            : {
                $gte: Math.min(oldPosition, newPosition),
                $lt: Math.max(oldPosition, newPosition),
            };
        await ConversationTag.updateMany({ user, position }, update);
    }
    /**
     * Updates an existing conversation tag.
     */
    async function updateConversationTag(user, oldTag, data) {
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            const Conversation = mongoose.models.Conversation;
            const { tag: newTag, description, position } = data;
            const existingTag = await ConversationTag.findOne({ user, tag: oldTag }).lean();
            if (!existingTag) {
                return null;
            }
            if (newTag && newTag !== oldTag) {
                const tagAlreadyExists = await ConversationTag.findOne({ user, tag: newTag }).lean();
                if (tagAlreadyExists) {
                    throw new Error('Tag already exists');
                }
                await Conversation.updateMany({ user, tags: oldTag }, { $set: { 'tags.$': newTag } });
            }
            const updateData = {};
            if (newTag) {
                updateData.tag = newTag;
            }
            if (description !== undefined) {
                updateData.description = description;
            }
            if (position !== undefined) {
                await adjustPositions(user, existingTag.position, position);
                updateData.position = position;
            }
            return await ConversationTag.findOneAndUpdate({ user, tag: oldTag }, updateData, {
                new: true,
                lean: true,
            });
        }
        catch (error) {
            winston.error('[updateConversationTag] Error updating conversation tag', error);
            throw new Error('Error updating conversation tag');
        }
    }
    /**
     * Deletes a conversation tag.
     */
    async function deleteConversationTag(user, tag) {
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            const Conversation = mongoose.models.Conversation;
            const deletedTag = await ConversationTag.findOneAndDelete({ user, tag }).lean();
            if (!deletedTag) {
                return null;
            }
            await Conversation.updateMany({ user, tags: tag }, { $pullAll: { tags: [tag] } });
            await ConversationTag.updateMany({ user, position: { $gt: deletedTag.position } }, { $inc: { position: -1 } });
            return deletedTag;
        }
        catch (error) {
            winston.error('[deleteConversationTag] Error deleting conversation tag', error);
            throw new Error('Error deleting conversation tag');
        }
    }
    /**
     * Updates tags for a specific conversation.
     */
    async function updateTagsForConversation(user, conversationId, tags) {
        var _a;
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            const Conversation = mongoose.models.Conversation;
            const conversation = await Conversation.findOne({ user, conversationId }).lean();
            if (!conversation) {
                throw new Error('Conversation not found');
            }
            const oldTags = new Set((_a = conversation.tags) !== null && _a !== void 0 ? _a : []);
            const newTags = new Set(tags);
            const addedTags = [...newTags].filter((tag) => !oldTags.has(tag));
            const removedTags = [...oldTags].filter((tag) => !newTags.has(tag));
            const bulkOps = [];
            for (const tag of addedTags) {
                bulkOps.push({
                    updateOne: {
                        filter: { user, tag },
                        update: { $inc: { count: 1 } },
                        upsert: true,
                    },
                });
            }
            for (const tag of removedTags) {
                bulkOps.push({
                    updateOne: {
                        filter: { user, tag },
                        update: { $inc: { count: -1 } },
                    },
                });
            }
            if (bulkOps.length > 0) {
                await tenantBulkWrite.tenantSafeBulkWrite(ConversationTag, bulkOps);
            }
            const updatedConversation = (await Conversation.findOneAndUpdate({ user, conversationId }, { $set: { tags: [...newTags] } }, { new: true })).toObject();
            return updatedConversation.tags;
        }
        catch (error) {
            winston.error('[updateTagsForConversation] Error updating tags', error);
            throw new Error('Error updating tags for conversation');
        }
    }
    /**
     * Increments tag counts for existing tags only.
     */
    async function bulkIncrementTagCounts(user, tags) {
        if (!tags || tags.length === 0) {
            return;
        }
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            const uniqueTags = [...new Set(tags.filter(Boolean))];
            if (uniqueTags.length === 0) {
                return;
            }
            const bulkOps = uniqueTags.map((tag) => ({
                updateOne: {
                    filter: { user, tag },
                    update: { $inc: { count: 1 } },
                },
            }));
            const result = await tenantBulkWrite.tenantSafeBulkWrite(ConversationTag, bulkOps);
            if (result && result.modifiedCount > 0) {
                winston.debug(`user: ${user} | Incremented tag counts - modified ${result.modifiedCount} tags`);
            }
        }
        catch (error) {
            winston.error('[bulkIncrementTagCounts] Error incrementing tag counts', error);
        }
    }
    /**
     * Deletes all conversation tags matching the given filter.
     */
    async function deleteConversationTags(filter) {
        try {
            const ConversationTag = mongoose.models.ConversationTag;
            const result = await ConversationTag.deleteMany(filter);
            return result.deletedCount;
        }
        catch (error) {
            winston.error('[deleteConversationTags] Error deleting conversation tags', error);
            throw new Error('Error deleting conversation tags');
        }
    }
    return {
        getConversationTags,
        createConversationTag,
        updateConversationTag,
        deleteConversationTag,
        deleteConversationTags,
        bulkIncrementTagCounts,
        updateTagsForConversation,
    };
}

exports.createConversationTagMethods = createConversationTagMethods;
//# sourceMappingURL=conversationTag.cjs.map
