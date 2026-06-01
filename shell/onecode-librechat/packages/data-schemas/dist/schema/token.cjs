'use strict';

var mongoose = require('mongoose');

const tokenSchema = new mongoose.Schema({
    userId: {
        type: mongoose.Schema.Types.ObjectId,
        required: true,
        ref: 'user',
    },
    email: {
        type: String,
    },
    type: {
        type: String,
    },
    identifier: {
        type: String,
    },
    token: {
        type: String,
        required: true,
    },
    createdAt: {
        type: Date,
        required: true,
        default: Date.now,
    },
    expiresAt: {
        type: Date,
        required: true,
    },
    metadata: {
        type: Map,
        of: mongoose.Schema.Types.Mixed,
    },
    tenantId: {
        type: String,
        index: true,
    },
});
tokenSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

module.exports = tokenSchema;
//# sourceMappingURL=token.cjs.map
