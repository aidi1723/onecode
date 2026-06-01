'use strict';

var mongoose = require('mongoose');

const pluginAuthSchema = new mongoose.Schema({
    authField: {
        type: String,
        required: true,
    },
    value: {
        type: String,
        required: true,
    },
    userId: {
        type: String,
        required: true,
    },
    pluginKey: {
        type: String,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });

module.exports = pluginAuthSchema;
//# sourceMappingURL=pluginAuth.cjs.map
