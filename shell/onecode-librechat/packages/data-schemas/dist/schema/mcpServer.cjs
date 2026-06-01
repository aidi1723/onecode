'use strict';

var mongoose = require('mongoose');

const mcpServerSchema = new mongoose.Schema({
    serverName: {
        type: String,
        index: true,
        required: true,
    },
    config: {
        type: mongoose.Schema.Types.Mixed,
        required: true,
        // Config contains: title, description, url, oauth, etc.
    },
    author: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
        index: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});
mcpServerSchema.index({ serverName: 1, tenantId: 1 }, { unique: true });
mcpServerSchema.index({ updatedAt: -1, _id: 1 });

module.exports = mcpServerSchema;
//# sourceMappingURL=mcpServer.cjs.map
