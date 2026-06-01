'use strict';

var mongoose = require('mongoose');

const keySchema = new mongoose.Schema({
    userId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    name: {
        type: String,
        required: true,
    },
    value: {
        type: String,
        required: true,
    },
    expiresAt: {
        type: Date,
    },
    tenantId: {
        type: String,
        index: true,
    },
});
keySchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

module.exports = keySchema;
//# sourceMappingURL=key.cjs.map
