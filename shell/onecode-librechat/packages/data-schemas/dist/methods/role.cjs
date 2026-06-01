'use strict';

var librechatDataProvider = require('librechat-data-provider');
var winston = require('../config/winston.cjs');

const systemRoleValues = new Set(Object.values(librechatDataProvider.SystemRoles));
/** Case-insensitive check — the legacy roles route uppercases params. */
function isSystemRoleName(name) {
    return systemRoleValues.has(name.toUpperCase());
}
class RoleConflictError extends Error {
    constructor(message) {
        super(message);
        this.name = 'RoleConflictError';
    }
}
function createRoleMethods(mongoose, deps = {}) {
    /**
     * Initialize default roles in the system.
     * Creates the default roles (ADMIN, USER) if they don't exist in the database.
     * Updates existing roles with new permission types if they're missing.
     */
    async function initializeRoles() {
        var _a, _b;
        const Role = mongoose.models.Role;
        for (const roleName of [librechatDataProvider.SystemRoles.ADMIN, librechatDataProvider.SystemRoles.USER]) {
            let role = await Role.findOne({ name: roleName });
            const defaultPerms = librechatDataProvider.roleDefaults[roleName].permissions;
            if (!role) {
                role = new Role({ ...librechatDataProvider.roleDefaults[roleName], description: '' });
            }
            else {
                if (role.description == null) {
                    role.description = '';
                }
                const permissions = (_b = (_a = role.toObject()) === null || _a === void 0 ? void 0 : _a.permissions) !== null && _b !== void 0 ? _b : {};
                role.permissions = role.permissions || {};
                for (const permType of Object.keys(defaultPerms)) {
                    if (permissions[permType] == null || Object.keys(permissions[permType]).length === 0) {
                        role.permissions[permType] = defaultPerms[permType];
                    }
                }
            }
            await role.save();
        }
    }
    /**
     * List all roles in the system. Returns only name and description (projected).
     */
    async function listRoles(options) {
        var _a, _b;
        const Role = mongoose.models.Role;
        const limit = (_a = options === null || options === void 0 ? void 0 : options.limit) !== null && _a !== void 0 ? _a : 50;
        const offset = (_b = options === null || options === void 0 ? void 0 : options.offset) !== null && _b !== void 0 ? _b : 0;
        return await Role.find({})
            .select('name description')
            .sort({ name: 1 })
            .skip(offset)
            .limit(limit)
            .lean();
    }
    async function countRoles() {
        const Role = mongoose.models.Role;
        return await Role.countDocuments({});
    }
    /**
     * Retrieve a role by name and convert the found role document to a plain object.
     * If the role with the given name doesn't exist and the name is a system defined role,
     * create it and return the lean version.
     */
    async function getRoleByName(roleName, fieldsToSelect = null) {
        var _a;
        const cache = (_a = deps.getCache) === null || _a === void 0 ? void 0 : _a.call(deps, librechatDataProvider.CacheKeys.ROLES);
        try {
            if (cache) {
                const cachedRole = await cache.get(roleName);
                if (cachedRole) {
                    return cachedRole;
                }
            }
            const Role = mongoose.models.Role;
            let query = Role.findOne({ name: roleName });
            if (fieldsToSelect) {
                query = query.select(fieldsToSelect);
            }
            const role = await query.lean().exec();
            if (!role && systemRoleValues.has(roleName)) {
                const newRole = await new Role(librechatDataProvider.roleDefaults[roleName]).save();
                if (cache) {
                    await cache.set(roleName, newRole);
                }
                return newRole.toObject();
            }
            if (cache) {
                await cache.set(roleName, role);
            }
            return role;
        }
        catch (error) {
            throw new Error(`Failed to retrieve or create role: ${error.message}`);
        }
    }
    /**
     * Update role values by name.
     */
    async function updateRoleByName(roleName, updates) {
        var _a, _b;
        const cache = (_a = deps.getCache) === null || _a === void 0 ? void 0 : _a.call(deps, librechatDataProvider.CacheKeys.ROLES);
        try {
            const Role = mongoose.models.Role;
            const role = await Role.findOneAndUpdate({ name: roleName }, { $set: updates }, { new: true })
                .select('-__v')
                .lean()
                .exec();
            if (cache) {
                if (updates.name && updates.name !== roleName) {
                    await Promise.all([cache.set(roleName, null), cache.set(updates.name, role)]);
                }
                else {
                    await cache.set(roleName, role);
                }
            }
            return role;
        }
        catch (error) {
            if (error && typeof error === 'object' && 'code' in error && error.code === 11000) {
                const targetName = (_b = updates.name) !== null && _b !== void 0 ? _b : roleName;
                throw new RoleConflictError(`Role "${targetName}" already exists`);
            }
            const updateError = new Error(`Failed to update role: ${error.message}`);
            updateError.cause = error;
            throw updateError;
        }
    }
    /**
     * Updates access permissions for a specific role and multiple permission types.
     */
    async function updateAccessPermissions(roleName, permissionsUpdate, roleData) {
        var _a;
        const updates = {};
        for (const [permissionType, permissions] of Object.entries(permissionsUpdate)) {
            if (librechatDataProvider.permissionsSchema.shape &&
                librechatDataProvider.permissionsSchema.shape[permissionType]) {
                updates[permissionType] = librechatDataProvider.removeNullishValues(permissions);
            }
        }
        if (!Object.keys(updates).length) {
            return;
        }
        try {
            const role = roleData !== null && roleData !== void 0 ? roleData : (await getRoleByName(roleName));
            if (!role) {
                return;
            }
            const currentPermissions = role.permissions || {};
            const updatedPermissions = { ...currentPermissions };
            let hasChanges = false;
            const unsetFields = {};
            const permissionTypes = Object.keys(librechatDataProvider.permissionsSchema.shape || {});
            for (const permType of permissionTypes) {
                if (role[permType] &&
                    typeof role[permType] === 'object') {
                    winston.info(`Migrating '${roleName}' role from old schema: found '${permType}' at top level`);
                    updatedPermissions[permType] = {
                        ...updatedPermissions[permType],
                        ...role[permType],
                    };
                    unsetFields[permType] = 1;
                    hasChanges = true;
                }
            }
            // Migrate legacy SHARED_GLOBAL → SHARE for PROMPTS and AGENTS.
            // SHARED_GLOBAL was removed in favour of SHARE in PR #11283. If the DB still has
            // SHARED_GLOBAL but not SHARE, inherit the value so sharing intent is preserved.
            const legacySharedGlobalTypes = ['PROMPTS', 'AGENTS'];
            for (const legacyPermType of legacySharedGlobalTypes) {
                const existingTypePerms = currentPermissions[legacyPermType];
                if (existingTypePerms &&
                    'SHARED_GLOBAL' in existingTypePerms &&
                    !('SHARE' in existingTypePerms) &&
                    updates[legacyPermType] &&
                    // Don't override an explicit SHARE value the caller already provided
                    !('SHARE' in updates[legacyPermType])) {
                    const inheritedValue = existingTypePerms['SHARED_GLOBAL'];
                    updates[legacyPermType]['SHARE'] = inheritedValue;
                    winston.info(`Migrating '${roleName}' role ${legacyPermType}.SHARED_GLOBAL=${inheritedValue} → SHARE`);
                }
            }
            for (const [permissionType, permissions] of Object.entries(updates)) {
                const currentTypePermissions = currentPermissions[permissionType] || {};
                updatedPermissions[permissionType] = { ...currentTypePermissions };
                for (const [permission, value] of Object.entries(permissions)) {
                    if (currentTypePermissions[permission] !== value) {
                        updatedPermissions[permissionType][permission] = value;
                        hasChanges = true;
                        winston.info(`Updating '${roleName}' role permission '${permissionType}' '${permission}' from ${currentTypePermissions[permission]} to: ${value}`);
                    }
                }
            }
            // Clean up orphaned SHARED_GLOBAL fields left in DB after the schema rename.
            // Since we $set the full permissions object, deleting from updatedPermissions
            // is sufficient to remove the field from MongoDB.
            for (const legacyPermType of legacySharedGlobalTypes) {
                const existingTypePerms = currentPermissions[legacyPermType];
                if (existingTypePerms && 'SHARED_GLOBAL' in existingTypePerms) {
                    if (!updates[legacyPermType]) {
                        // permType wasn't in the update payload so the migration block above didn't run.
                        // Create a writable copy and handle the SHARED_GLOBAL → SHARE inheritance here
                        // to avoid removing SHARED_GLOBAL without writing SHARE (data loss).
                        updatedPermissions[legacyPermType] = { ...existingTypePerms };
                        if (!('SHARE' in existingTypePerms)) {
                            updatedPermissions[legacyPermType]['SHARE'] = existingTypePerms['SHARED_GLOBAL'];
                            winston.info(`Migrating '${roleName}' role ${legacyPermType}.SHARED_GLOBAL=${existingTypePerms['SHARED_GLOBAL']} → SHARE`);
                        }
                    }
                    delete updatedPermissions[legacyPermType]['SHARED_GLOBAL'];
                    hasChanges = true;
                    winston.info(`Removed legacy SHARED_GLOBAL field from '${roleName}' role ${legacyPermType} permissions`);
                }
            }
            if (hasChanges) {
                const Role = mongoose.models.Role;
                const updateObj = { permissions: updatedPermissions };
                if (Object.keys(unsetFields).length > 0) {
                    winston.info(`Unsetting old schema fields for '${roleName}' role: ${Object.keys(unsetFields).join(', ')}`);
                    try {
                        await Role.updateOne({ name: roleName }, {
                            $set: updateObj,
                            $unset: unsetFields,
                        });
                        const cache = (_a = deps.getCache) === null || _a === void 0 ? void 0 : _a.call(deps, librechatDataProvider.CacheKeys.ROLES);
                        const updatedRole = await Role.findOne({ name: roleName }).select('-__v').lean().exec();
                        if (cache) {
                            await cache.set(roleName, updatedRole);
                        }
                        winston.info(`Updated role '${roleName}' and removed old schema fields`);
                    }
                    catch (updateError) {
                        winston.error(`Error during role migration update: ${updateError.message}`);
                        throw updateError;
                    }
                }
                else {
                    await updateRoleByName(roleName, updateObj);
                }
                winston.info(`Updated '${roleName}' role permissions`);
            }
            else {
                winston.info(`No changes needed for '${roleName}' role permissions`);
            }
        }
        catch (error) {
            winston.error(`Failed to update ${roleName} role permissions:`, error);
        }
    }
    /**
     * Migrates roles from old schema to new schema structure.
     */
    async function migrateRoleSchema(roleName) {
        var _a;
        try {
            const Role = mongoose.models.Role;
            let roles;
            if (roleName) {
                const role = await Role.findOne({ name: roleName });
                roles = role ? [role] : [];
            }
            else {
                roles = await Role.find({});
            }
            winston.info(`Migrating ${roles.length} roles to new schema structure`);
            let migratedCount = 0;
            for (const role of roles) {
                const permissionTypes = Object.keys(librechatDataProvider.permissionsSchema.shape || {});
                const unsetFields = {};
                let hasOldSchema = false;
                for (const permType of permissionTypes) {
                    if (role[permType] && typeof role[permType] === 'object') {
                        hasOldSchema = true;
                        role.permissions = role.permissions || {};
                        role.permissions[permType] = {
                            ...role.permissions[permType],
                            ...role[permType],
                        };
                        unsetFields[permType] = 1;
                    }
                }
                if (hasOldSchema) {
                    try {
                        winston.info(`Migrating role '${role.name}' from old schema structure`);
                        await Role.updateOne({ _id: role._id }, {
                            $set: { permissions: role.permissions },
                            $unset: unsetFields,
                        });
                        const cache = (_a = deps.getCache) === null || _a === void 0 ? void 0 : _a.call(deps, librechatDataProvider.CacheKeys.ROLES);
                        if (cache) {
                            const updatedRole = await Role.findById(role._id).lean().exec();
                            await cache.set(role.name, updatedRole);
                        }
                        migratedCount++;
                        winston.info(`Migrated role '${role.name}'`);
                    }
                    catch (error) {
                        winston.error(`Failed to migrate role '${role.name}': ${error.message}`);
                    }
                }
            }
            winston.info(`Migration complete: ${migratedCount} roles migrated`);
            return migratedCount;
        }
        catch (error) {
            winston.error(`Role schema migration failed: ${error.message}`);
            throw error;
        }
    }
    /** Rejects names that match system roles. */
    async function createRoleByName(roleData) {
        var _a;
        const { name } = roleData;
        if (!name || typeof name !== 'string' || !name.trim()) {
            throw new Error('Role name is required');
        }
        const trimmed = name.trim();
        if (isSystemRoleName(trimmed)) {
            throw new RoleConflictError(`Cannot create role with reserved system name: ${name}`);
        }
        const Role = mongoose.models.Role;
        const existing = await Role.findOne({ name: trimmed }).lean();
        if (existing) {
            throw new RoleConflictError(`Role "${trimmed}" already exists`);
        }
        let role;
        try {
            role = await new Role({ ...roleData, name: trimmed }).save();
        }
        catch (err) {
            /**
             * The compound unique index `{ name: 1, tenantId: 1 }` on the role schema
             * (roleSchema.index in schema/role.ts) triggers error 11000 when a concurrent
             * request races past the findOne check above. This catch converts it into
             * the same user-facing message as the application-level duplicate check.
             */
            if (err && typeof err === 'object' && 'code' in err && err.code === 11000) {
                throw new RoleConflictError(`Role "${trimmed}" already exists`);
            }
            throw err;
        }
        try {
            const cache = (_a = deps.getCache) === null || _a === void 0 ? void 0 : _a.call(deps, librechatDataProvider.CacheKeys.ROLES);
            if (cache) {
                await cache.set(role.name, role.toObject());
            }
        }
        catch (cacheError) {
            winston.error(`[createRoleByName] cache set failed for "${role.name}":`, cacheError);
        }
        return role.toObject();
    }
    /**
     * Guards against deleting system roles. Reassigns affected users back to USER.
     *
     * No existence pre-check is performed: for a nonexistent role the `updateMany`
     * is a harmless no-op and `findOneAndDelete` returns null. This makes the
     * function idempotent — a retry after a partial failure will still clean up
     * orphaned user references and cache entries.
     *
     * Without a MongoDB transaction the two writes are non-atomic — if the delete
     * fails after the reassignment, users will already have been moved to USER
     * while the role document still exists. Recovery requires the caller to retry
     * the delete call, which will succeed since the `updateMany` is a no-op on
     * the second pass.
     */
    async function deleteRoleByName(roleName) {
        var _a;
        if (isSystemRoleName(roleName)) {
            throw new Error(`Cannot delete system role: ${roleName}`);
        }
        const Role = mongoose.models.Role;
        const User = mongoose.models.User;
        await User.updateMany({ role: roleName }, { $set: { role: librechatDataProvider.SystemRoles.USER } });
        const deleted = await Role.findOneAndDelete({ name: roleName }).lean();
        try {
            const cache = (_a = deps.getCache) === null || _a === void 0 ? void 0 : _a.call(deps, librechatDataProvider.CacheKeys.ROLES);
            if (cache) {
                // Setting null evicts the stale document. getRoleByName treats falsy cached
                // values as a miss and falls through to the DB, so this does not provide
                // negative caching — it only prevents serving the pre-deletion document.
                await cache.set(roleName, null);
            }
        }
        catch (cacheError) {
            winston.error(`[deleteRoleByName] cache invalidation failed for "${roleName}":`, cacheError);
        }
        return deleted;
    }
    async function updateUsersByRole(oldRole, newRole) {
        const User = mongoose.models.User;
        await User.updateMany({ role: oldRole }, { $set: { role: newRole } });
    }
    async function findUserIdsByRole(roleName) {
        const User = mongoose.models.User;
        const users = await User.find({ role: roleName }).select('_id').lean();
        return users.map((u) => u._id.toString());
    }
    async function updateUsersRoleByIds(userIds, newRole) {
        if (userIds.length === 0) {
            return;
        }
        const User = mongoose.models.User;
        await User.updateMany({ _id: { $in: userIds } }, { $set: { role: newRole } });
    }
    async function listUsersByRole(roleName, options) {
        var _a, _b;
        const User = mongoose.models.User;
        const limit = (_a = options === null || options === void 0 ? void 0 : options.limit) !== null && _a !== void 0 ? _a : 50;
        const offset = (_b = options === null || options === void 0 ? void 0 : options.offset) !== null && _b !== void 0 ? _b : 0;
        return await User.find({ role: roleName })
            .select('_id name email avatar')
            .sort({ _id: 1 })
            .skip(offset)
            .limit(limit)
            .lean();
    }
    async function countUsersByRole(roleName) {
        const User = mongoose.models.User;
        return await User.countDocuments({ role: roleName });
    }
    return {
        listRoles,
        countRoles,
        initializeRoles,
        getRoleByName,
        updateRoleByName,
        updateAccessPermissions,
        migrateRoleSchema,
        createRoleByName,
        deleteRoleByName,
        updateUsersByRole,
        findUserIdsByRole,
        updateUsersRoleByIds,
        listUsersByRole,
        countUsersByRole,
    };
}

exports.RoleConflictError = RoleConflictError;
exports.createRoleMethods = createRoleMethods;
//# sourceMappingURL=role.cjs.map
