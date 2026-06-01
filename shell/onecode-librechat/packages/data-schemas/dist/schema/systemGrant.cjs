'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');
var capabilities = require('../admin/capabilities.cjs');

const systemGrantSchema = new mongoose.Schema({
    principalType: {
        type: String,
        enum: Object.values(librechatDataProvider.PrincipalType),
        required: true,
    },
    principalId: {
        type: mongoose.Schema.Types.Mixed,
        required: true,
    },
    capability: {
        type: String,
        required: true,
        validate: {
            validator: capabilities.isValidCapability,
            message: 'Invalid capability string: "{VALUE}"',
        },
    },
    /**
     * Platform-level grants MUST omit this field entirely — never set it to null.
     * Queries for platform-level grants use `{ tenantId: { $exists: false } }`, which
     * matches absent fields but NOT `null`. A document stored with `{ tenantId: null }`
     * would silently match neither platform-level nor tenant-scoped queries.
     */
    tenantId: {
        type: String,
        required: false,
        validate: {
            validator: (v) => v !== null && v !== '',
            message: 'tenantId must be a non-empty string or omitted entirely — never null or empty',
        },
    },
    grantedBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
    },
    grantedAt: {
        type: Date,
        default: Date.now,
    },
    /** Reserved for future TTL enforcement — time-bounded / temporary grants. Not enforced yet. */
    expiresAt: {
        type: Date,
        required: false,
    },
}, { timestamps: true });
/*
 * principalId normalization (string → ObjectId for USER/GROUP) is handled
 * explicitly by grantCapability — the only sanctioned write path.
 * All writes MUST go through grantCapability; do not use Model.create()
 * or save() directly, as there is no schema-level normalization hook.
 */
systemGrantSchema.index({ principalType: 1, principalId: 1, capability: 1, tenantId: 1 }, { unique: true });
systemGrantSchema.index({ capability: 1, tenantId: 1 });
systemGrantSchema.index({ principalType: 1, capability: 1, tenantId: 1 });

module.exports = systemGrantSchema;
//# sourceMappingURL=systemGrant.cjs.map
