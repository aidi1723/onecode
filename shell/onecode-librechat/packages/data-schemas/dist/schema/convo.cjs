'use strict';

var mongoose = require('mongoose');
var defaults = require('./defaults.cjs');

const convoSchema = new mongoose.Schema({
    conversationId: {
        type: String,
        required: true,
        index: true,
        meiliIndex: true,
    },
    title: {
        type: String,
        default: 'New Chat',
        meiliIndex: true,
    },
    user: {
        type: String,
        index: true,
        meiliIndex: true,
    },
    messages: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Message' }],
    isTemporary: {
        type: Boolean,
        default: false,
    },
    ...defaults.conversationPreset,
    agent_id: {
        type: String,
    },
    tags: {
        type: [String],
        default: [],
        meiliIndex: true,
    },
    files: {
        type: [String],
    },
    expiredAt: {
        type: Date,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
convoSchema.index({ expiredAt: 1 }, { expireAfterSeconds: 0 });
convoSchema.index({ createdAt: 1, updatedAt: 1 });
convoSchema.index({ conversationId: 1, user: 1, tenantId: 1 }, { unique: true });
convoSchema.index({ user: 1, isTemporary: 1, expiredAt: 1 });
// index for MeiliSearch sync operations
convoSchema.index({ _meiliIndex: 1, isTemporary: 1, expiredAt: 1 });

module.exports = convoSchema;
//# sourceMappingURL=convo.cjs.map
