'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');

/**
 * Uses a sub-schema for permissions. Notice we disable `_id` for this subdocument.
 */
const rolePermissionsSchema = new mongoose.Schema({
    [librechatDataProvider.PermissionTypes.BOOKMARKS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.PROMPTS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
        [librechatDataProvider.Permissions.CREATE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE_PUBLIC]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.MEMORIES]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
        [librechatDataProvider.Permissions.CREATE]: { type: Boolean },
        [librechatDataProvider.Permissions.UPDATE]: { type: Boolean },
        [librechatDataProvider.Permissions.READ]: { type: Boolean },
        [librechatDataProvider.Permissions.OPT_OUT]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.AGENTS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
        [librechatDataProvider.Permissions.CREATE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE_PUBLIC]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.MULTI_CONVO]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.TEMPORARY_CHAT]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.RUN_CODE]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.WEB_SEARCH]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.PEOPLE_PICKER]: {
        [librechatDataProvider.Permissions.VIEW_USERS]: { type: Boolean },
        [librechatDataProvider.Permissions.VIEW_GROUPS]: { type: Boolean },
        [librechatDataProvider.Permissions.VIEW_ROLES]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.MARKETPLACE]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.FILE_SEARCH]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.FILE_CITATIONS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.MCP_SERVERS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
        [librechatDataProvider.Permissions.CREATE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE_PUBLIC]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.REMOTE_AGENTS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
        [librechatDataProvider.Permissions.CREATE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE_PUBLIC]: { type: Boolean },
    },
    [librechatDataProvider.PermissionTypes.SKILLS]: {
        [librechatDataProvider.Permissions.USE]: { type: Boolean },
        [librechatDataProvider.Permissions.CREATE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE]: { type: Boolean },
        [librechatDataProvider.Permissions.SHARE_PUBLIC]: { type: Boolean },
    },
}, { _id: false });
const roleSchema = new mongoose.Schema({
    name: { type: String, required: true, index: true },
    description: { type: String, default: '' },
    permissions: {
        type: rolePermissionsSchema,
    },
    tenantId: {
        type: String,
        index: true,
    },
});
roleSchema.index({ name: 1, tenantId: 1 }, { unique: true });

module.exports = roleSchema;
//# sourceMappingURL=role.cjs.map
