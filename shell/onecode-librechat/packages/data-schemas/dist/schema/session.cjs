'use strict';

var mongoose = require('mongoose');

const sessionSchema = new mongoose.Schema({
    refreshTokenHash: {
        type: String,
        required: true,
    },
    expiration: {
        type: Date,
        required: true,
        expires: 0,
    },
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
});

module.exports = sessionSchema;
//# sourceMappingURL=session.cjs.map
