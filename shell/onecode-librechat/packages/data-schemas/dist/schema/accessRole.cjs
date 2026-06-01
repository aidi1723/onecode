'use strict';

var mongoose = require('mongoose');

const accessRoleSchema = new mongoose.Schema({
    accessRoleId: {
        type: String,
        required: true,
        index: true,
    },
    name: {
        type: String,
        required: true,
    },
    description: String,
    resourceType: {
        type: String,
        enum: ['agent', 'project', 'file', 'promptGroup', 'mcpServer', 'remoteAgent', 'skill'],
        required: true,
        default: 'agent',
    },
    permBits: {
        type: Number,
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
accessRoleSchema.index({ accessRoleId: 1, tenantId: 1 }, { unique: true });

module.exports = accessRoleSchema;
//# sourceMappingURL=accessRole.cjs.map
