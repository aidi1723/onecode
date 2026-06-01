'use strict';

var mongoose = require('mongoose');

const conversationTag = new mongoose.Schema({
    tag: {
        type: String,
        index: true,
    },
    user: {
        type: String,
        index: true,
    },
    description: {
        type: String,
        index: true,
    },
    count: {
        type: Number,
        default: 0,
    },
    position: {
        type: Number,
        default: 0,
        index: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
// Create a compound index on tag and user with unique constraint.
conversationTag.index({ tag: 1, user: 1, tenantId: 1 }, { unique: true });

module.exports = conversationTag;
//# sourceMappingURL=conversationTag.cjs.map
