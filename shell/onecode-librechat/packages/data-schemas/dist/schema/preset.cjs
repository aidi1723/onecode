'use strict';

var mongoose = require('mongoose');
var defaults = require('./defaults.cjs');

const presetSchema = new mongoose.Schema({
    presetId: {
        type: String,
        required: true,
        index: true,
    },
    title: {
        type: String,
        default: 'New Chat',
        meiliIndex: true,
    },
    user: {
        type: String,
        default: null,
    },
    defaultPreset: {
        type: Boolean,
    },
    order: {
        type: Number,
    },
    ...defaults.conversationPreset,
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
presetSchema.index({ presetId: 1, tenantId: 1 }, { unique: true });

module.exports = presetSchema;
//# sourceMappingURL=preset.cjs.map
