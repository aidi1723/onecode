'use strict';

var crypto = require('node:crypto');
var librechatDataProvider = require('librechat-data-provider');
var winston = require('../config/winston.cjs');

const { mcp_delimiter } = librechatDataProvider.Constants;
/**
 * Mirrors `TOOL_RESOURCE_KEYS` in `@librechat/api` — the subset of
 * `EToolResources` that actually carries `file_ids` on an agent document.
 * `code_interpreter` is excluded (it belongs to the Assistants API, not
 * `AgentToolResources`) to avoid emitting dead MongoDB clauses.
 */
const TOOL_RESOURCE_KEYS = [
    librechatDataProvider.EToolResources.execute_code,
    librechatDataProvider.EToolResources.file_search,
    librechatDataProvider.EToolResources.image_edit,
    librechatDataProvider.EToolResources.context,
    librechatDataProvider.EToolResources.ocr,
];
/**
 * Extracts unique MCP server names from tools array.
 * Tools format: "toolName_mcp_serverName" or "sys__server__sys_mcp_serverName"
 */
function extractMCPServerNames(tools) {
    if (!tools || !Array.isArray(tools)) {
        return [];
    }
    const serverNames = new Set();
    for (const tool of tools) {
        if (!tool || !tool.includes(mcp_delimiter)) {
            continue;
        }
        const parts = tool.split(mcp_delimiter);
        if (parts.length >= 2) {
            serverNames.add(parts[parts.length - 1]);
        }
    }
    return Array.from(serverNames);
}
/**
 * Check if a version already exists in the versions array, excluding timestamp and author fields.
 */
function isDuplicateVersion(updateData, currentData, versions, actionsHash = null) {
    if (!versions || versions.length === 0) {
        return null;
    }
    const excludeFields = [
        '_id',
        'id',
        'createdAt',
        'updatedAt',
        'author',
        'updatedBy',
        'created_at',
        'updated_at',
        '__v',
        'versions',
        'actionsHash',
    ];
    const { $push: _$push, $pull: _$pull, $addToSet: _$addToSet, ...directUpdates } = updateData;
    if (Object.keys(directUpdates).length === 0 && !actionsHash) {
        return null;
    }
    const wouldBeVersion = { ...currentData, ...directUpdates };
    const lastVersion = versions[versions.length - 1];
    if (actionsHash && lastVersion.actionsHash !== actionsHash) {
        return null;
    }
    const allFields = new Set([...Object.keys(wouldBeVersion), ...Object.keys(lastVersion)]);
    const importantFields = Array.from(allFields).filter((field) => !excludeFields.includes(field));
    let isMatch = true;
    for (const field of importantFields) {
        const wouldBeValue = wouldBeVersion[field];
        const lastVersionValue = lastVersion[field];
        if (!wouldBeValue && !lastVersionValue) {
            continue;
        }
        // Handle arrays
        if (Array.isArray(wouldBeValue) || Array.isArray(lastVersionValue)) {
            let wouldBeArr;
            if (Array.isArray(wouldBeValue)) {
                wouldBeArr = wouldBeValue;
            }
            else if (wouldBeValue == null) {
                wouldBeArr = [];
            }
            else {
                wouldBeArr = [wouldBeValue];
            }
            let lastVersionArr;
            if (Array.isArray(lastVersionValue)) {
                lastVersionArr = lastVersionValue;
            }
            else if (lastVersionValue == null) {
                lastVersionArr = [];
            }
            else {
                lastVersionArr = [lastVersionValue];
            }
            if (wouldBeArr.length !== lastVersionArr.length) {
                isMatch = false;
                break;
            }
            if (wouldBeArr.length > 0 && typeof wouldBeArr[0] === 'object' && wouldBeArr[0] !== null) {
                const sortedWouldBe = [...wouldBeArr].map((item) => JSON.stringify(item)).sort();
                const sortedVersion = [...lastVersionArr].map((item) => JSON.stringify(item)).sort();
                if (!sortedWouldBe.every((item, i) => item === sortedVersion[i])) {
                    isMatch = false;
                    break;
                }
            }
            else {
                const sortedWouldBe = [...wouldBeArr].sort();
                const sortedVersion = [...lastVersionArr].sort();
                if (!sortedWouldBe.every((item, i) => item === sortedVersion[i])) {
                    isMatch = false;
                    break;
                }
            }
        }
        // Handle objects
        else if (typeof wouldBeValue === 'object' && wouldBeValue !== null) {
            const lastVersionObj = typeof lastVersionValue === 'object' && lastVersionValue !== null ? lastVersionValue : {};
            const wouldBeKeys = Object.keys(wouldBeValue);
            const lastVersionKeys = Object.keys(lastVersionObj);
            if (wouldBeKeys.length === 0 && lastVersionKeys.length === 0) {
                continue;
            }
            if (JSON.stringify(wouldBeValue) !== JSON.stringify(lastVersionObj)) {
                isMatch = false;
                break;
            }
        }
        // Handle primitive values
        else {
            if (wouldBeValue !== lastVersionValue) {
                if (typeof wouldBeValue === 'boolean' &&
                    wouldBeValue === false &&
                    lastVersionValue === undefined) {
                    continue;
                }
                if (typeof wouldBeValue === 'string' &&
                    wouldBeValue === '' &&
                    lastVersionValue === undefined) {
                    continue;
                }
                isMatch = false;
                break;
            }
        }
    }
    return isMatch ? lastVersion : null;
}
/**
 * Generates a hash of action metadata for version comparison.
 */
async function generateActionMetadataHash(actionIds, actions) {
    if (!actionIds || actionIds.length === 0) {
        return '';
    }
    const actionMap = new Map();
    actions.forEach((action) => {
        actionMap.set(action.action_id, action.metadata);
    });
    const sortedActionIds = [...actionIds].sort();
    const metadataString = sortedActionIds
        .map((actionFullId) => {
        const parts = actionFullId.split(librechatDataProvider.actionDelimiter);
        const actionId = parts[1];
        const metadata = actionMap.get(actionId);
        if (!metadata) {
            return `${actionId}:null`;
        }
        const sortedKeys = Object.keys(metadata).sort();
        const metadataStr = sortedKeys
            .map((key) => `${key}:${JSON.stringify(metadata[key])}`)
            .join(',');
        return `${actionId}:{${metadataStr}}`;
    })
        .join(';');
    const encoder = new TextEncoder();
    const data = encoder.encode(metadataString);
    const hashBuffer = await crypto.webcrypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
}
function createAgentMethods(mongoose, deps) {
    const { removeAllPermissions, getActions, getSoleOwnedResourceIds } = deps;
    /**
     * Create an agent with the provided data.
     */
    async function createAgent(agentData) {
        const Agent = mongoose.models.Agent;
        const { author: _author, ...versionData } = agentData;
        const timestamp = new Date();
        const initialAgentData = {
            ...agentData,
            versions: [
                {
                    ...versionData,
                    createdAt: timestamp,
                    updatedAt: timestamp,
                },
            ],
            category: agentData.category || 'general',
            mcpServerNames: extractMCPServerNames(agentData.tools),
        };
        return (await Agent.create(initialAgentData)).toObject();
    }
    /**
     * Get an agent document based on the provided search parameter.
     */
    async function getAgent(searchParameter) {
        const Agent = mongoose.models.Agent;
        return await Agent.findOne(searchParameter).lean();
    }
    /**
     * Get multiple agent documents based on the provided search parameters.
     */
    async function getAgents(searchParameter) {
        const Agent = mongoose.models.Agent;
        return await Agent.find(searchParameter).lean();
    }
    async function hasAgentWithMCPServerName({ agentIds, serverName, }) {
        if (agentIds.length === 0) {
            return false;
        }
        const Agent = mongoose.models.Agent;
        const agent = await Agent.exists({
            _id: { $in: agentIds },
            mcpServerNames: serverName,
        });
        return agent !== null;
    }
    async function getMCPServerNamesByAgentIds(agentIds) {
        var _a;
        if (agentIds.length === 0) {
            return [];
        }
        const Agent = mongoose.models.Agent;
        const agents = await Agent.find({
            _id: { $in: agentIds },
            mcpServerNames: { $exists: true, $not: { $size: 0 } },
        }, { mcpServerNames: 1 }).lean();
        const serverNames = new Set();
        for (const agent of agents) {
            for (const serverName of (_a = agent.mcpServerNames) !== null && _a !== void 0 ? _a : []) {
                serverNames.add(serverName);
            }
        }
        return Array.from(serverNames);
    }
    /**
     * Update an agent with new data without overwriting existing properties,
     * or create a new agent if it doesn't exist.
     * When an agent is updated, a copy of the current state will be saved to the versions array.
     */
    async function updateAgent(searchParameter, updateData, options = {}) {
        const Agent = mongoose.models.Agent;
        const { updatingUserId = null, forceVersion = false, skipVersioning = false } = options;
        const mongoOptions = { new: true, upsert: false };
        const currentAgent = await Agent.findOne(searchParameter);
        if (currentAgent) {
            const { __v, _id, id: __id, versions, author: _author, ...versionData } = currentAgent.toObject();
            const { $push, $pull, $addToSet, ...directUpdates } = updateData;
            // Sync mcpServerNames when tools are updated
            if (directUpdates.tools !== undefined) {
                const mcpServerNames = extractMCPServerNames(directUpdates.tools);
                directUpdates.mcpServerNames = mcpServerNames;
                updateData.mcpServerNames = mcpServerNames;
            }
            let actionsHash = null;
            // Generate actions hash if agent has actions
            if (currentAgent.actions && currentAgent.actions.length > 0) {
                const actionIds = currentAgent.actions
                    .map((action) => {
                    const parts = action.split(librechatDataProvider.actionDelimiter);
                    return parts[1];
                })
                    .filter(Boolean);
                if (actionIds.length > 0) {
                    try {
                        const actions = await getActions({ action_id: { $in: actionIds } }, true);
                        actionsHash = await generateActionMetadataHash(currentAgent.actions, actions);
                    }
                    catch (error) {
                        winston.error('Error fetching actions for hash generation:', error);
                    }
                }
            }
            const shouldCreateVersion = !skipVersioning &&
                (forceVersion || Object.keys(directUpdates).length > 0 || $push || $pull || $addToSet);
            if (shouldCreateVersion) {
                const duplicateVersion = isDuplicateVersion(updateData, versionData, versions, actionsHash);
                if (duplicateVersion && !forceVersion) {
                    const agentObj = currentAgent.toObject();
                    agentObj.version = versions.length;
                    return agentObj;
                }
            }
            const versionEntry = {
                ...versionData,
                ...directUpdates,
                updatedAt: new Date(),
            };
            if (actionsHash) {
                versionEntry.actionsHash = actionsHash;
            }
            if (updatingUserId) {
                versionEntry.updatedBy = new mongoose.Types.ObjectId(updatingUserId);
            }
            if (shouldCreateVersion) {
                updateData.$push = {
                    ...($push || {}),
                    versions: versionEntry,
                };
            }
        }
        return (await Agent.findOneAndUpdate(searchParameter, updateData, mongoOptions).lean());
    }
    /**
     * Modifies an agent with the resource file id.
     */
    async function addAgentResourceFile({ agent_id, tool_resource, file_id, updatingUserId, }) {
        const Agent = mongoose.models.Agent;
        const searchParameter = { id: agent_id };
        const agent = await getAgent(searchParameter);
        if (!agent) {
            throw new Error('Agent not found for adding resource file');
        }
        const fileIdsPath = `tool_resources.${tool_resource}.file_ids`;
        await Agent.updateOne({
            id: agent_id,
            [`${fileIdsPath}`]: { $exists: false },
        }, {
            $set: {
                [`${fileIdsPath}`]: [],
            },
        });
        const updateDataObj = {
            $addToSet: {
                tools: tool_resource,
                [fileIdsPath]: file_id,
            },
        };
        const updatedAgent = await updateAgent(searchParameter, updateDataObj, {
            updatingUserId,
        });
        if (updatedAgent) {
            return updatedAgent;
        }
        else {
            throw new Error('Agent not found for adding resource file');
        }
    }
    /**
     * Removes multiple resource files from an agent using atomic operations.
     */
    async function removeAgentResourceFiles({ agent_id, files, }) {
        const Agent = mongoose.models.Agent;
        const searchParameter = { id: agent_id };
        const filesByResource = files.reduce((acc, { tool_resource, file_id }) => {
            if (!acc[tool_resource]) {
                acc[tool_resource] = [];
            }
            acc[tool_resource].push(file_id);
            return acc;
        }, {});
        const pullAllOps = {};
        for (const [resource, fileIds] of Object.entries(filesByResource)) {
            const fileIdsPath = `tool_resources.${resource}.file_ids`;
            pullAllOps[fileIdsPath] = fileIds;
        }
        const updatePullData = { $pullAll: pullAllOps };
        const agentAfterPull = (await Agent.findOneAndUpdate(searchParameter, updatePullData, {
            new: true,
        }).lean());
        if (!agentAfterPull) {
            const agentExists = await getAgent(searchParameter);
            if (!agentExists) {
                throw new Error('Agent not found for removing resource files');
            }
            throw new Error('Failed to update agent during file removal (pull step)');
        }
        return agentAfterPull;
    }
    /**
     * Removes the given file_ids from every agent's `tool_resources.*.file_ids`
     * so file deletion cannot leave orphaned stubs behind (see issue #12776).
     */
    async function removeAgentResourceFilesFromAllAgents({ file_ids, }) {
        var _a, _b;
        if (!file_ids || file_ids.length === 0) {
            return { matchedCount: 0, modifiedCount: 0 };
        }
        const Agent = mongoose.models.Agent;
        const orQuery = TOOL_RESOURCE_KEYS.map((key) => ({
            [`tool_resources.${key}.file_ids`]: { $in: file_ids },
        }));
        const pullAllOps = TOOL_RESOURCE_KEYS.reduce((acc, key) => {
            acc[`tool_resources.${key}.file_ids`] = file_ids;
            return acc;
        }, {});
        const result = await Agent.updateMany({ $or: orQuery }, { $pullAll: pullAllOps });
        return {
            matchedCount: (_a = result.matchedCount) !== null && _a !== void 0 ? _a : 0,
            modifiedCount: (_b = result.modifiedCount) !== null && _b !== void 0 ? _b : 0,
        };
    }
    /**
     * Deletes an agent based on the provided search parameter.
     */
    async function deleteAgent(searchParameter) {
        const Agent = mongoose.models.Agent;
        const User = mongoose.models.User;
        const agent = await Agent.findOneAndDelete(searchParameter);
        if (agent) {
            await Promise.all([
                removeAllPermissions({
                    resourceType: librechatDataProvider.ResourceType.AGENT,
                    resourceId: agent._id,
                }),
                removeAllPermissions({
                    resourceType: librechatDataProvider.ResourceType.REMOTE_AGENT,
                    resourceId: agent._id,
                }),
            ]);
            try {
                await Agent.updateMany({ 'edges.to': agent.id }, { $pull: { edges: { to: agent.id } } });
            }
            catch (error) {
                winston.error('[deleteAgent] Error removing agent from handoff edges', error);
            }
            try {
                await User.updateMany({ 'favorites.agentId': agent.id }, { $pull: { favorites: { agentId: agent.id } } });
            }
            catch (error) {
                winston.error('[deleteAgent] Error removing agent from user favorites', error);
            }
        }
        return agent ? agent.toObject() : null;
    }
    /**
     * Deletes agents solely owned by the user and cleans up their ACLs.
     * Agents with other owners are left intact; the caller is responsible for
     * removing the user's own ACL principal entries separately.
     *
     * Also handles legacy (pre-ACL) agents that only have the author field set,
     * ensuring they are not orphaned if no permission migration has been run.
     */
    async function deleteUserAgents(userId) {
        const Agent = mongoose.models.Agent;
        const AclEntry = mongoose.models.AclEntry;
        const User = mongoose.models.User;
        try {
            const userObjectId = new mongoose.Types.ObjectId(userId);
            const soleOwnedObjectIds = await getSoleOwnedResourceIds(userObjectId, [
                librechatDataProvider.ResourceType.AGENT,
                librechatDataProvider.ResourceType.REMOTE_AGENT,
            ]);
            const authoredAgents = await Agent.find({ author: userObjectId }).select('id _id').lean();
            const migratedEntries = authoredAgents.length > 0
                ? await AclEntry.find({
                    resourceType: { $in: [librechatDataProvider.ResourceType.AGENT, librechatDataProvider.ResourceType.REMOTE_AGENT] },
                    resourceId: { $in: authoredAgents.map((a) => a._id) },
                })
                    .select('resourceId')
                    .lean()
                : [];
            const migratedIds = new Set(migratedEntries.map((e) => e.resourceId.toString()));
            const legacyAgents = authoredAgents.filter((a) => !migratedIds.has(a._id.toString()));
            const soleOwnedAgents = soleOwnedObjectIds.length > 0
                ? await Agent.find({ _id: { $in: soleOwnedObjectIds } })
                    .select('id _id')
                    .lean()
                : [];
            const allAgents = [...soleOwnedAgents, ...legacyAgents];
            if (allAgents.length === 0) {
                return;
            }
            const agentIds = allAgents.map((agent) => agent.id);
            const agentObjectIds = allAgents.map((agent) => agent._id);
            await AclEntry.deleteMany({
                resourceType: { $in: [librechatDataProvider.ResourceType.AGENT, librechatDataProvider.ResourceType.REMOTE_AGENT] },
                resourceId: { $in: agentObjectIds },
            });
            try {
                await Agent.updateMany({ 'edges.to': { $in: agentIds } }, { $pull: { edges: { to: { $in: agentIds } } } });
            }
            catch (error) {
                winston.error('[deleteUserAgents] Error removing agents from handoff edges', error);
            }
            try {
                await User.updateMany({ 'favorites.agentId': { $in: agentIds } }, { $pull: { favorites: { agentId: { $in: agentIds } } } });
            }
            catch (error) {
                winston.error('[deleteUserAgents] Error removing agents from user favorites', error);
            }
            await Agent.deleteMany({ _id: { $in: agentObjectIds } });
        }
        catch (error) {
            winston.error('[deleteUserAgents] General error:', error);
        }
    }
    /**
     * Get agents by accessible IDs with cursor pagination. Defaults to a 100-page
     * limit (max 1000); pass `limit: null` to opt out entirely.
     */
    async function getListAgentsByAccess({ accessibleIds = [], otherParams = {}, limit = 100, after = null, includeSkillConfig = false, }) {
        const Agent = mongoose.models.Agent;
        const isPaginated = limit !== null && limit !== undefined;
        const normalizedLimit = isPaginated
            ? Math.min(Math.max(1, parseInt(String(limit)) || 20), 1000)
            : null;
        const baseQuery = {
            ...otherParams,
            _id: { $in: accessibleIds },
        };
        if (after) {
            try {
                const cursor = JSON.parse(Buffer.from(after, 'base64').toString('utf8'));
                const { updatedAt, _id } = cursor;
                const cursorCondition = {
                    $or: [
                        { updatedAt: { $lt: new Date(updatedAt) } },
                        {
                            updatedAt: new Date(updatedAt),
                            _id: { $gt: new mongoose.Types.ObjectId(_id) },
                        },
                    ],
                };
                if (Object.keys(baseQuery).length > 0) {
                    baseQuery.$and = [{ ...baseQuery }, cursorCondition];
                    Object.keys(baseQuery).forEach((key) => {
                        if (key !== '$and')
                            delete baseQuery[key];
                    });
                }
                else {
                    Object.assign(baseQuery, cursorCondition);
                }
            }
            catch (error) {
                winston.warn('Invalid cursor:', error.message);
            }
        }
        const projection = {
            id: 1,
            _id: 1,
            name: 1,
            avatar: 1,
            author: 1,
            description: 1,
            updatedAt: 1,
            category: 1,
            support_contact: 1,
            is_promoted: 1,
        };
        if (includeSkillConfig) {
            projection.skills = 1;
            projection.skills_enabled = 1;
        }
        let query = Agent.find(baseQuery, projection).sort({ updatedAt: -1, _id: 1 });
        if (isPaginated && normalizedLimit) {
            query = query.limit(normalizedLimit + 1);
        }
        const agents = (await query.lean());
        const hasMore = isPaginated && normalizedLimit ? agents.length > normalizedLimit : false;
        const data = (isPaginated && normalizedLimit ? agents.slice(0, normalizedLimit) : agents).map((agent) => {
            if (agent.author) {
                agent.author = agent.author.toString();
            }
            return agent;
        });
        let nextCursor = null;
        if (isPaginated && hasMore && data.length > 0 && normalizedLimit) {
            const lastAgent = agents[normalizedLimit - 1];
            nextCursor = Buffer.from(JSON.stringify({
                updatedAt: lastAgent.updatedAt.toISOString(),
                _id: lastAgent._id.toString(),
            })).toString('base64');
        }
        return {
            object: 'list',
            data,
            first_id: data.length > 0 ? data[0].id : null,
            last_id: data.length > 0 ? data[data.length - 1].id : null,
            has_more: hasMore,
            after: nextCursor,
        };
    }
    /**
     * Reverts an agent to a specific version in its version history.
     */
    async function revertAgentVersion(searchParameter, versionIndex) {
        const Agent = mongoose.models.Agent;
        const agent = await Agent.findOne(searchParameter);
        if (!agent) {
            throw new Error('Agent not found');
        }
        if (!agent.versions || !agent.versions[versionIndex]) {
            throw new Error(`Version ${versionIndex} not found`);
        }
        const revertToVersion = { ...agent.versions[versionIndex] };
        delete revertToVersion._id;
        delete revertToVersion.id;
        delete revertToVersion.versions;
        delete revertToVersion.author;
        delete revertToVersion.updatedBy;
        const revertedAgent = await Agent.findOneAndUpdate(searchParameter, revertToVersion, {
            new: true,
        }).lean();
        if (!revertedAgent) {
            throw new Error('Agent not found');
        }
        return revertedAgent;
    }
    /**
     * Counts the number of promoted agents.
     */
    async function countPromotedAgents() {
        const Agent = mongoose.models.Agent;
        return await Agent.countDocuments({ is_promoted: true });
    }
    /** Removes an agent from the favorites of specified users. */
    async function removeAgentFromUserFavorites(resourceId, userIds) {
        const Agent = mongoose.models.Agent;
        const User = mongoose.models.User;
        const agent = await Agent.findOne({ _id: resourceId }, { id: 1 }).lean();
        if (!agent) {
            return;
        }
        await User.updateMany({ _id: { $in: userIds }, 'favorites.agentId': agent.id }, { $pull: { favorites: { agentId: agent.id } } });
    }
    return {
        getAgent,
        getAgents,
        createAgent,
        hasAgentWithMCPServerName,
        getMCPServerNamesByAgentIds,
        updateAgent,
        deleteAgent,
        deleteUserAgents,
        revertAgentVersion,
        countPromotedAgents,
        addAgentResourceFile,
        getListAgentsByAccess,
        removeAgentResourceFiles,
        generateActionMetadataHash,
        removeAgentFromUserFavorites,
        removeAgentResourceFilesFromAllAgents,
    };
}

exports.createAgentMethods = createAgentMethods;
//# sourceMappingURL=agent.cjs.map
