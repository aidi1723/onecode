'use strict';

var mongoose = require('mongoose');

const promptSchema = new mongoose.Schema({
    groupId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'PromptGroup',
        required: true,
        index: true,
    },
    author: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
        index: true,
    },
    prompt: {
        type: String,
        required: true,
    },
    type: {
        type: String,
        enum: ['text', 'chat'],
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});
promptSchema.index({ createdAt: 1, updatedAt: 1 });

module.exports = promptSchema;
//# sourceMappingURL=prompt.cjs.map
