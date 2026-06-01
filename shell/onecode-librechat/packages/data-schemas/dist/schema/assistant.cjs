'use strict';

var mongoose = require('mongoose');

const assistantSchema = new mongoose.Schema({
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    assistant_id: {
        type: String,
        index: true,
        required: true,
    },
    avatar: {
        type: mongoose.Schema.Types.Mixed,
        default: undefined,
    },
    conversation_starters: {
        type: [String],
        default: [],
    },
    access_level: {
        type: Number,
    },
    file_ids: { type: [String], default: undefined },
    actions: { type: [String], default: undefined },
    append_current_datetime: {
        type: Boolean,
        default: false,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});

module.exports = assistantSchema;
//# sourceMappingURL=assistant.cjs.map
