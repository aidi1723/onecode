'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');
var permissions = require('../common/permissions.cjs');

const aclEntrySchema = new mongoose.Schema({
    principalType: {
        type: String,
        enum: Object.values(librechatDataProvider.PrincipalType),
        required: true,
    },
    principalId: {
        type: mongoose.Schema.Types.Mixed, // Can be ObjectId for users/groups or String for roles
        refPath: 'principalModel',
        required: function () {
            return this.principalType !== librechatDataProvider.PrincipalType.PUBLIC;
        },
        index: true,
    },
    principalModel: {
        type: String,
        enum: Object.values(librechatDataProvider.PrincipalModel),
        required: function () {
            return this.principalType !== librechatDataProvider.PrincipalType.PUBLIC;
        },
    },
    resourceType: {
        type: String,
        enum: Object.values(librechatDataProvider.ResourceType),
        required: true,
    },
    resourceId: {
        type: mongoose.Schema.Types.ObjectId,
        required: true,
        index: true,
    },
    permBits: {
        type: Number,
        default: 1,
        min: 0,
        max: permissions.MAX_PERM_BITS,
        validate: {
            validator: Number.isInteger,
            message: '`permBits` must be an integer',
        },
    },
    roleId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'AccessRole',
    },
    inheritedFrom: {
        type: mongoose.Schema.Types.ObjectId,
        sparse: true,
        index: true,
    },
    grantedBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
    },
    grantedAt: {
        type: Date,
        default: Date.now,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
aclEntrySchema.index({
    principalId: 1,
    principalType: 1,
    resourceType: 1,
    resourceId: 1,
    tenantId: 1,
});
aclEntrySchema.index({ resourceId: 1, principalType: 1, principalId: 1, tenantId: 1 });
aclEntrySchema.index({ principalId: 1, permBits: 1, resourceType: 1, tenantId: 1 });
/** Covers `findPublicResourceIds` and the public branch of `findAccessibleResources`. */
aclEntrySchema.index({ principalType: 1, resourceType: 1, permBits: 1, resourceId: 1 });

module.exports = aclEntrySchema;
//# sourceMappingURL=aclEntry.cjs.map
