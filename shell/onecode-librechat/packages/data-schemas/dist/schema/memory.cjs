'use strict';

var mongoose = require('mongoose');

const MemoryEntrySchema = new mongoose.Schema({
    userId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        index: true,
        required: true,
    },
    key: {
        type: String,
        required: true,
        validate: {
            validator: (v) => /^[a-z_]+$/.test(v),
            message: 'Key must only contain lowercase letters and underscores',
        },
    },
    value: {
        type: String,
        required: true,
    },
    tokenCount: {
        type: Number,
        default: 0,
    },
    updated_at: {
        type: Date,
        default: Date.now,
    },
    tenantId: {
        type: String,
        index: true,
    },
});

module.exports = MemoryEntrySchema;
//# sourceMappingURL=memory.cjs.map
