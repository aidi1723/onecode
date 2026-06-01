'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');
var string = require('../utils/string.cjs');

function createUserGroupMethods(mongoose$1) {
    /**
     * Find a group by its ID
     * @param groupId - The group ID
     * @param projection - Optional projection of fields to return
     * @param session - Optional MongoDB session for transactions
     * @returns The group document or null if not found
     */
    async function findGroupById(groupId, projection = {}, session) {
        const Group = mongoose$1.models.Group;
        const query = Group.findOne({ _id: groupId }, projection);
        if (session) {
            query.session(session);
        }
        return await query.lean();
    }
    /**
     * Find a group by its external ID (e.g., Entra ID)
     * @param idOnTheSource - The external ID
     * @param source - The source ('entra' or 'local')
     * @param projection - Optional projection of fields to return
     * @param session - Optional MongoDB session for transactions
     * @returns The group document or null if not found
     */
    async function findGroupByExternalId(idOnTheSource, source = 'entra', projection = {}, session) {
        const Group = mongoose$1.models.Group;
        const query = Group.findOne({ idOnTheSource, source }, projection);
        if (session) {
            query.session(session);
        }
        return await query.lean();
    }
    /**
     * Find multiple groups by their external IDs (e.g., Entra IDs) in a single query
     * @param idsOnTheSource - Array of external IDs
     * @param source - The source ('entra' or 'local')
     * @param session - Optional MongoDB session for transactions
     * @returns Array of group documents
     */
    async function findGroupsByExternalIds(idsOnTheSource, source = 'entra', session) {
        const Group = mongoose$1.models.Group;
        const query = Group.find({ idOnTheSource: { $in: idsOnTheSource }, source }, { idOnTheSource: 1, _id: 0 });
        if (session) {
            query.session(session);
        }
        return await query.lean();
    }
    /**
     * Find groups by name pattern (case-insensitive partial match)
     * @param namePattern - The name pattern to search for
     * @param source - Optional source filter ('entra', 'local', or null for all)
     * @param limit - Maximum number of results to return
     * @param session - Optional MongoDB session for transactions
     * @returns Array of matching groups
     */
    async function findGroupsByNamePattern(namePattern, source = null, limit = 20, session) {
        const Group = mongoose$1.models.Group;
        const regex = new RegExp(string.escapeRegExp(namePattern), 'i');
        const query = {
            $or: [{ name: regex }, { email: regex }, { description: regex }],
        };
        if (source) {
            query.source = source;
        }
        const dbQuery = Group.find(query).limit(limit);
        if (session) {
            dbQuery.session(session);
        }
        return await dbQuery.lean();
    }
    /**
     * Find all groups a user is a member of by their ID or idOnTheSource
     * @param userId - The user ID
     * @param session - Optional MongoDB session for transactions
     * @returns Array of groups the user is a member of
     */
    async function findGroupsByMemberId(userId, session) {
        const User = mongoose$1.models.User;
        const Group = mongoose$1.models.Group;
        const userQuery = User.findById(userId, 'idOnTheSource');
        if (session) {
            userQuery.session(session);
        }
        const user = await userQuery.lean();
        if (!user) {
            return [];
        }
        const userIdOnTheSource = user.idOnTheSource || userId.toString();
        const query = Group.find({ memberIds: userIdOnTheSource });
        if (session) {
            query.session(session);
        }
        return await query.lean();
    }
    /**
     * Create a new group
     * @param groupData - Group data including name, source, and optional idOnTheSource
     * @param session - Optional MongoDB session for transactions
     * @returns The created group
     */
    async function createGroup(groupData, session) {
        const Group = mongoose$1.models.Group;
        const options = session ? { session } : {};
        return await Group.create([groupData], options).then((groups) => groups[0]);
    }
    /**
     * Update or create a group by external ID
     * @param idOnTheSource - The external ID
     * @param source - The source ('entra' or 'local')
     * @param updateData - Data to update or set if creating
     * @param session - Optional MongoDB session for transactions
     * @returns The updated or created group
     */
    async function upsertGroupByExternalId(idOnTheSource, source, updateData, session) {
        const Group = mongoose$1.models.Group;
        const options = {
            new: true,
            upsert: true,
            ...(session ? { session } : {}),
        };
        return await Group.findOneAndUpdate({ idOnTheSource, source }, { $set: updateData }, options);
    }
    /**
     * Add a user to a group
     * Only updates Group.memberIds (one-way relationship)
     * Note: memberIds stores idOnTheSource values, not ObjectIds
     *
     * @param userId - The user ID
     * @param groupId - The group ID to add
     * @param session - Optional MongoDB session for transactions
     * @returns The user and updated group documents
     */
    async function addUserToGroup(userId, groupId, session) {
        const User = mongoose$1.models.User;
        const Group = mongoose$1.models.Group;
        const options = { new: true, ...(session ? { session } : {}) };
        const user = await User.findById(userId, 'idOnTheSource', options).lean();
        if (!user) {
            throw new Error(`User not found: ${userId}`);
        }
        const userIdOnTheSource = user.idOnTheSource || userId.toString();
        const updatedGroup = await Group.findByIdAndUpdate(groupId, { $addToSet: { memberIds: userIdOnTheSource } }, options).lean();
        return { user: user, group: updatedGroup };
    }
    /**
     * Remove a user from a group
     * Only updates Group.memberIds (one-way relationship)
     * Note: memberIds stores idOnTheSource values, not ObjectIds
     *
     * @param userId - The user ID
     * @param groupId - The group ID to remove
     * @param session - Optional MongoDB session for transactions
     * @returns The user and updated group documents
     */
    async function removeUserFromGroup(userId, groupId, session) {
        const User = mongoose$1.models.User;
        const Group = mongoose$1.models.Group;
        const options = { new: true, ...(session ? { session } : {}) };
        const user = await User.findById(userId, 'idOnTheSource', options).lean();
        if (!user) {
            throw new Error(`User not found: ${userId}`);
        }
        const userIdOnTheSource = user.idOnTheSource || userId.toString();
        const updatedGroup = await Group.findByIdAndUpdate(groupId, { $pullAll: { memberIds: [userIdOnTheSource] } }, options).lean();
        return { user: user, group: updatedGroup };
    }
    /**
     * Get all groups a user is a member of
     * @param userId - The user ID
     * @param session - Optional MongoDB session for transactions
     * @returns Array of group documents
     */
    async function getUserGroups(userId, session) {
        return await findGroupsByMemberId(userId, session);
    }
    /**
     * Get a list of all principal identifiers for a user (user ID + group IDs + public).
     * For use in permission checks.
     *
     * Tenant filtering for group memberships is handled automatically by the
     * `applyTenantIsolation` Mongoose plugin on the Group schema. The
     * `tenantContextMiddleware` (chained by `requireJwtAuth` after passport auth)
     * sets the ALS context, so `getUserGroups()` → `findGroupsByMemberId()` queries
     * are scoped to the requesting tenant. No explicit tenantId parameter is needed.
     *
     * IMPORTANT: This relies on the ALS tenant context being active. If this
     * function is called outside a request context (e.g. startup, background jobs),
     * group queries will be unscoped. In strict mode, the Mongoose plugin will
     * reject such queries.
     *
     * Ref: #12091 (resolved by tenant context middleware in requireJwtAuth)
     *
     * @param params - Parameters object
     * @param params.userId - The user ID
     * @param params.role - Optional user role (if not provided, will query from DB)
     * @param session - Optional MongoDB session for transactions
     * @returns Array of principal objects with type and id
     */
    async function getUserPrincipals(params, session) {
        const { userId, role } = params;
        /** `userId` must be an `ObjectId` for USER principal since ACL entries store `ObjectId`s */
        const userObjectId = typeof userId === 'string' ? new mongoose.Types.ObjectId(userId) : userId;
        const principals = [{ principalType: librechatDataProvider.PrincipalType.USER, principalId: userObjectId }];
        // If role is not provided, query user to get it
        let userRole = role;
        if (userRole === undefined) {
            const User = mongoose$1.models.User;
            const query = User.findById(userId).select('role');
            if (session) {
                query.session(session);
            }
            const user = await query.lean();
            userRole = user === null || user === void 0 ? void 0 : user.role;
        }
        // Add role as a principal if user has one
        if (userRole && userRole.trim()) {
            principals.push({ principalType: librechatDataProvider.PrincipalType.ROLE, principalId: userRole });
        }
        const userGroups = await getUserGroups(userId, session);
        if (userGroups && userGroups.length > 0) {
            userGroups.forEach((group) => {
                principals.push({ principalType: librechatDataProvider.PrincipalType.GROUP, principalId: group._id });
            });
        }
        principals.push({ principalType: librechatDataProvider.PrincipalType.PUBLIC });
        return principals;
    }
    /**
     * Sync a user's Entra ID group memberships
     * @param userId - The user ID
     * @param entraGroups - Array of Entra groups with id and name
     * @param session - Optional MongoDB session for transactions
     * @returns The updated user with new group memberships
     */
    async function syncUserEntraGroups(userId, entraGroups, session) {
        var _a;
        const User = mongoose$1.models.User;
        const Group = mongoose$1.models.Group;
        const query = User.findById(userId, { idOnTheSource: 1 });
        if (session) {
            query.session(session);
        }
        const user = await query.lean();
        if (!user) {
            throw new Error(`User not found: ${userId}`);
        }
        /** Get user's idOnTheSource for storing in group.memberIds */
        const userIdOnTheSource = user.idOnTheSource || userId.toString();
        const entraIdMap = new Map();
        const addedGroups = [];
        const removedGroups = [];
        for (const entraGroup of entraGroups) {
            entraIdMap.set(entraGroup.id, true);
            let group = await findGroupByExternalId(entraGroup.id, 'entra', {}, session);
            if (!group) {
                group = await createGroup({
                    name: entraGroup.name,
                    description: entraGroup.description,
                    email: entraGroup.email,
                    idOnTheSource: entraGroup.id,
                    source: 'entra',
                    memberIds: [userIdOnTheSource],
                }, session);
                addedGroups.push(group);
            }
            else if (!((_a = group.memberIds) === null || _a === void 0 ? void 0 : _a.includes(userIdOnTheSource))) {
                const { group: updatedGroup } = await addUserToGroup(userId, group._id, session);
                if (updatedGroup) {
                    addedGroups.push(updatedGroup);
                }
            }
        }
        const groupsQuery = Group.find({ source: 'entra', memberIds: userIdOnTheSource }, { _id: 1, idOnTheSource: 1 });
        if (session) {
            groupsQuery.session(session);
        }
        const existingGroups = await groupsQuery.lean();
        for (const group of existingGroups) {
            if (group.idOnTheSource && !entraIdMap.has(group.idOnTheSource)) {
                const { group: removedGroup } = await removeUserFromGroup(userId, group._id, session);
                if (removedGroup) {
                    removedGroups.push(removedGroup);
                }
            }
        }
        const userQuery = User.findById(userId);
        if (session) {
            userQuery.session(session);
        }
        const updatedUser = await userQuery.lean();
        if (!updatedUser) {
            throw new Error(`User not found after update: ${userId}`);
        }
        return {
            user: updatedUser,
            addedGroups,
            removedGroups,
        };
    }
    /**
     * Calculate relevance score for a search result
     * @param item - The search result item
     * @param searchPattern - The search pattern
     * @returns Relevance score (0-100)
     */
    function calculateRelevanceScore(item, searchPattern) {
        const normalizedPattern = searchPattern.toLowerCase();
        /** Get searchable text based on type */
        const searchableFields = item.type === librechatDataProvider.PrincipalType.USER
            ? [item.name, item.email, item.username].filter(Boolean)
            : [item.name, item.email, item.description].filter(Boolean);
        let maxScore = 0;
        for (const field of searchableFields) {
            if (!field)
                continue;
            const fieldLower = field.toLowerCase();
            let score = 0;
            /** Exact match gets highest score */
            if (fieldLower === normalizedPattern) {
                score = 100;
            }
            else if (fieldLower.startsWith(normalizedPattern)) {
                /** Starts with query gets high score */
                score = 80;
            }
            else if (fieldLower.includes(normalizedPattern)) {
                /** Contains query gets medium score */
                score = 50;
            }
            else {
                /** Default score for database match */
                score = 10;
            }
            maxScore = Math.max(maxScore, score);
        }
        return maxScore;
    }
    /**
     * Sort principals by relevance score and type priority
     * @param results - Array of results with _searchScore property
     * @returns Sorted array
     */
    function sortPrincipalsByRelevance(results) {
        return results.sort((a, b) => {
            if (b._searchScore !== a._searchScore) {
                return (b._searchScore || 0) - (a._searchScore || 0);
            }
            if (a.type !== b.type) {
                return a.type === librechatDataProvider.PrincipalType.USER ? -1 : 1;
            }
            const aName = a.name || a.email || '';
            const bName = b.name || b.email || '';
            return aName.localeCompare(bName);
        });
    }
    /**
     * Transform user object to TPrincipalSearchResult format
     * @param user - User object from database
     * @returns Transformed user result
     */
    function transformUserToTPrincipalSearchResult(user) {
        return {
            id: user.id,
            type: librechatDataProvider.PrincipalType.USER,
            name: user.name || user.email,
            email: user.email,
            username: user.username,
            avatar: user.avatar,
            provider: user.provider,
            source: 'local',
            idOnTheSource: user.idOnTheSource || user.id,
        };
    }
    /**
     * Transform group object to TPrincipalSearchResult format
     * @param group - Group object from database
     * @returns Transformed group result
     */
    function transformGroupToTPrincipalSearchResult(group) {
        var _a, _b;
        return {
            id: (_a = group._id) === null || _a === void 0 ? void 0 : _a.toString(),
            type: librechatDataProvider.PrincipalType.GROUP,
            name: group.name,
            email: group.email,
            avatar: group.avatar,
            description: group.description,
            source: group.source || 'local',
            memberCount: group.memberIds ? group.memberIds.length : 0,
            idOnTheSource: group.idOnTheSource || ((_b = group._id) === null || _b === void 0 ? void 0 : _b.toString()),
        };
    }
    /**
     * Search for principals (users and groups) by pattern matching on name/email
     * Returns combined results in TPrincipalSearchResult format without sorting
     * @param searchPattern - The pattern to search for
     * @param limitPerType - Maximum number of results to return
     * @param typeFilter - Optional array of types to filter by, or null for all types
     * @param session - Optional MongoDB session for transactions
     * @returns Array of principals in TPrincipalSearchResult format
     */
    async function searchPrincipals(searchPattern, limitPerType = 10, typeFilter = null, session) {
        if (!searchPattern || searchPattern.trim().length === 0) {
            return [];
        }
        const trimmedPattern = searchPattern.trim();
        const escapedPattern = string.escapeRegExp(trimmedPattern);
        const promises = [];
        if (!typeFilter || typeFilter.includes(librechatDataProvider.PrincipalType.USER)) {
            /** Note: searchUsers is imported from ~/models and needs to be passed in or implemented */
            const userFields = 'name email username avatar provider idOnTheSource';
            /** For now, we'll use a direct query instead of searchUsers */
            const User = mongoose$1.models.User;
            const regex = new RegExp(escapedPattern, 'i');
            const userQuery = User.find({
                $or: [{ name: regex }, { email: regex }, { username: regex }],
            })
                .select(userFields)
                .limit(limitPerType);
            if (session) {
                userQuery.session(session);
            }
            promises.push(userQuery.lean().then((users) => users.map((user) => {
                var _a;
                const userWithId = user;
                return transformUserToTPrincipalSearchResult({
                    id: ((_a = userWithId._id) === null || _a === void 0 ? void 0 : _a.toString()) || '',
                    name: userWithId.name,
                    email: userWithId.email,
                    username: userWithId.username,
                    avatar: userWithId.avatar,
                    provider: userWithId.provider,
                });
            })));
        }
        else {
            promises.push(Promise.resolve([]));
        }
        if (!typeFilter || typeFilter.includes(librechatDataProvider.PrincipalType.GROUP)) {
            promises.push(findGroupsByNamePattern(trimmedPattern, null, limitPerType, session).then((groups) => groups.map(transformGroupToTPrincipalSearchResult)));
        }
        else {
            promises.push(Promise.resolve([]));
        }
        if (!typeFilter || typeFilter.includes(librechatDataProvider.PrincipalType.ROLE)) {
            const Role = mongoose$1.models.Role;
            if (Role) {
                const regex = new RegExp(escapedPattern, 'i');
                const roleQuery = Role.find({ name: regex }).select('name').limit(limitPerType);
                if (session) {
                    roleQuery.session(session);
                }
                promises.push(roleQuery.lean().then((roles) => roles.map((role) => ({
                    /** Role name as ID */
                    id: role.name,
                    type: librechatDataProvider.PrincipalType.ROLE,
                    name: role.name,
                    source: 'local',
                    idOnTheSource: role.name,
                }))));
            }
        }
        else {
            promises.push(Promise.resolve([]));
        }
        const results = await Promise.all(promises);
        const combined = results.flat();
        return combined;
    }
    /**
     * Removes a user from all groups they belong to.
     * @param userId - The user ID (or ObjectId) of the member to remove
     */
    async function removeUserFromAllGroups(userId) {
        const Group = mongoose$1.models.Group;
        await Group.updateMany({ memberIds: userId }, { $pullAll: { memberIds: [userId] } });
    }
    /**
     * Finds a single group matching the given filter.
     * @param filter - MongoDB filter query
     */
    async function findGroupByQuery(filter, session) {
        const Group = mongoose$1.models.Group;
        const query = Group.findOne(filter);
        if (session) {
            query.session(session);
        }
        return query.lean();
    }
    /**
     * Updates a group by its ID.
     * @param groupId - The group's ObjectId
     * @param data - Fields to set via $set
     */
    async function updateGroupById(groupId, data, session) {
        const Group = mongoose$1.models.Group;
        const options = { new: true, ...(session ? { session } : {}) };
        return Group.findByIdAndUpdate(groupId, { $set: data }, options).lean();
    }
    /**
     * Bulk-updates groups matching a filter.
     * @param filter - MongoDB filter query
     * @param update - Update operations
     * @param options - Optional query options (e.g., { session })
     */
    async function bulkUpdateGroups(filter, update, options) {
        const Group = mongoose$1.models.Group;
        return Group.updateMany(filter, update, options || {});
    }
    function buildGroupQuery(filter) {
        const query = {};
        if (filter.source) {
            query.source = filter.source;
        }
        if (filter.search) {
            const regex = new RegExp(string.escapeRegExp(filter.search), 'i');
            query.$or = [{ name: regex }, { email: regex }, { description: regex }];
        }
        return query;
    }
    /**
     * List groups with optional source, search, and pagination filters.
     * Results are sorted by name.
     * @param filter - Optional filter with source, search, limit, and offset fields
     * @param session - Optional MongoDB session for transactions
     */
    async function listGroups(filter = {}, session) {
        var _a, _b;
        const Group = mongoose$1.models.Group;
        const query = buildGroupQuery(filter);
        const limit = (_a = filter.limit) !== null && _a !== void 0 ? _a : 50;
        const offset = (_b = filter.offset) !== null && _b !== void 0 ? _b : 0;
        return await Group.find(query)
            .sort({ name: 1 })
            .skip(offset)
            .limit(limit)
            .session(session !== null && session !== void 0 ? session : null)
            .lean();
    }
    /**
     * Count groups matching optional source and search filters.
     * @param filter - Optional filter with source and search fields
     * @param session - Optional MongoDB session for transactions
     */
    async function countGroups(filter = {}, session) {
        const Group = mongoose$1.models.Group;
        const query = buildGroupQuery(filter);
        return await Group.countDocuments(query).session(session !== null && session !== void 0 ? session : null);
    }
    /**
     * Delete a group by its ID.
     * @param groupId - The group's ObjectId
     * @param session - Optional MongoDB session for transactions
     */
    async function deleteGroup(groupId, session) {
        const Group = mongoose$1.models.Group;
        const options = session ? { session } : {};
        return await Group.findByIdAndDelete(groupId, options).lean();
    }
    /**
     * Remove a member from a group by raw memberId string ($pull from memberIds).
     * Unlike removeUserFromGroup, this does not look up the user first.
     * @param groupId - The group's ObjectId
     * @param memberId - The raw memberId string to remove (ObjectId or idOnTheSource)
     * @param session - Optional MongoDB session for transactions
     */
    async function removeMemberById(groupId, memberId, session) {
        const Group = mongoose$1.models.Group;
        const options = { new: true, ...(session ? { session } : {}) };
        return await Group.findByIdAndUpdate(groupId, { $pull: { memberIds: memberId } }, options).lean();
    }
    return {
        findGroupById,
        findGroupByExternalId,
        findGroupsByExternalIds,
        findGroupsByNamePattern,
        findGroupsByMemberId,
        createGroup,
        upsertGroupByExternalId,
        addUserToGroup,
        removeUserFromGroup,
        removeUserFromAllGroups,
        findGroupByQuery,
        updateGroupById,
        bulkUpdateGroups,
        getUserGroups,
        getUserPrincipals,
        syncUserEntraGroups,
        searchPrincipals,
        calculateRelevanceScore,
        sortPrincipalsByRelevance,
        listGroups,
        countGroups,
        deleteGroup,
        removeMemberById,
    };
}

exports.createUserGroupMethods = createUserGroupMethods;
//# sourceMappingURL=userGroup.cjs.map
