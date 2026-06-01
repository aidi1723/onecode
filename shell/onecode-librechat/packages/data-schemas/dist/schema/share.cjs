'use strict';

var mongoose = require('mongoose');

const shareSchema = new mongoose.Schema({
    conversationId: {
        type: String,
        required: true,
    },
    title: {
        type: String,
        index: true,
    },
    user: {
        type: String,
        index: true,
    },
    messages: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Message' }],
    shareId: {
        type: String,
        index: true,
    },
    targetMessageId: {
        type: String,
        required: false,
        index: true,
    },
    isPublic: {
        type: Boolean,
        default: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
    expiredAt: {
        type: Date,
    },
}, { timestamps: true });
shareSchema.index({ expiredAt: 1 }, { expireAfterSeconds: 0 });
shareSchema.index({ conversationId: 1, user: 1, targetMessageId: 1, tenantId: 1 });

module.exports = shareSchema;
//# sourceMappingURL=share.cjs.map
