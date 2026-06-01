'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');

const configSchema = new mongoose.Schema({
    principalType: {
        type: String,
        enum: Object.values(librechatDataProvider.PrincipalType),
        required: true,
        index: true,
    },
    principalId: {
        type: String,
        refPath: 'principalModel',
        required: true,
        index: true,
    },
    principalModel: {
        type: String,
        enum: Object.values(librechatDataProvider.PrincipalModel),
        required: true,
    },
    priority: {
        type: Number,
        required: true,
        index: true,
    },
    overrides: {
        type: mongoose.Schema.Types.Mixed,
        default: {},
    },
    isActive: {
        type: Boolean,
        default: true,
        index: true,
    },
    configVersion: {
        type: Number,
        default: 0,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
// Enforce 1:1 principal-to-config (one config document per principal per tenant)
configSchema.index({ principalType: 1, principalId: 1, tenantId: 1 }, { unique: true });
configSchema.index({ principalType: 1, principalId: 1, isActive: 1, tenantId: 1 });
configSchema.index({ priority: 1, isActive: 1, tenantId: 1 });

module.exports = configSchema;
//# sourceMappingURL=config.cjs.map
