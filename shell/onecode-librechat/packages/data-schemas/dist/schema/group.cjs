'use strict';

var mongoose = require('mongoose');

const groupSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true,
        index: true,
    },
    description: {
        type: String,
        required: false,
    },
    email: {
        type: String,
        required: false,
        index: true,
    },
    avatar: {
        type: String,
        required: false,
    },
    memberIds: [
        {
            type: String,
            required: false,
        },
    ],
    source: {
        type: String,
        enum: ['local', 'entra'],
        default: 'local',
    },
    /** External ID (e.g., Entra ID) */
    idOnTheSource: {
        type: String,
        sparse: true,
        index: true,
        required: function () {
            return this.source !== 'local';
        },
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
groupSchema.index({ idOnTheSource: 1, source: 1, tenantId: 1 }, {
    unique: true,
    partialFilterExpression: { idOnTheSource: { $exists: true } },
});
groupSchema.index({ memberIds: 1 });

module.exports = groupSchema;
//# sourceMappingURL=group.cjs.map
