'use strict';

var librechatDataProvider = require('librechat-data-provider');
var tenantContext = require('../config/tenantContext.cjs');
var objectId = require('../utils/objectId.cjs');
var string = require('../utils/string.cjs');
var winston = require('../config/winston.cjs');

function createPromptMethods(mongoose, deps) {
    const { getSoleOwnedResourceIds } = deps;
    const { ObjectId } = mongoose.Types;
    /**
     * Batch-fetches production prompts for an array of prompt groups
     * and attaches them as `productionPrompt` field.
     */
    async function attachProductionPrompts(groups) {
        const Prompt = mongoose.models.Prompt;
        const uniqueIds = [
            ...new Set(groups.map((g) => { var _a; return (_a = g.productionId) === null || _a === void 0 ? void 0 : _a.toString(); }).filter(Boolean)),
        ];
        if (uniqueIds.length === 0) {
            return groups.map((g) => ({ ...g, productionPrompt: null }));
        }
        const prompts = await Prompt.find({ _id: { $in: uniqueIds } })
            .select('prompt')
            .lean();
        const promptMap = new Map(prompts.map((p) => [p._id.toString(), p]));
        return groups.map((g) => {
            var _a;
            return ({
                ...g,
                productionPrompt: g.productionId
                    ? ((_a = promptMap.get(g.productionId.toString())) !== null && _a !== void 0 ? _a : null)
                    : null,
            });
        });
    }
    /**
     * Get all prompt groups with filters (no pagination).
     */
    async function getAllPromptGroups(filter) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            const { name, ...query } = filter;
            if (name) {
                query.name = new RegExp(string.escapeRegExp(name), 'i');
            }
            if (!query.category) {
                delete query.category;
            }
            else if (query.category === librechatDataProvider.SystemCategories.MY_PROMPTS) {
                delete query.category;
            }
            else if (query.category === librechatDataProvider.SystemCategories.NO_CATEGORY) {
                query.category = '';
            }
            else if (query.category === librechatDataProvider.SystemCategories.SHARED_PROMPTS) {
                delete query.category;
            }
            const groups = await PromptGroup.find(query)
                .sort({ numberOfGenerations: -1, updatedAt: -1, _id: 1 })
                .select('name numberOfGenerations oneliner category author authorName createdAt updatedAt command productionId')
                .lean();
            return await attachProductionPrompts(groups);
        }
        catch (error) {
            winston.error('Error getting all prompt groups', error);
            return { message: 'Error getting all prompt groups' };
        }
    }
    /**
     * Get prompt groups with pagination and filters.
     */
    async function getPromptGroups(filter) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            const { pageNumber = 1, pageSize = 10, name, ...query } = filter;
            const validatedPageNumber = Math.max(parseInt(String(pageNumber), 10), 1);
            const validatedPageSize = Math.max(parseInt(String(pageSize), 10), 1);
            if (name) {
                query.name = new RegExp(string.escapeRegExp(name), 'i');
            }
            if (!query.category) {
                delete query.category;
            }
            else if (query.category === librechatDataProvider.SystemCategories.MY_PROMPTS) {
                delete query.category;
            }
            else if (query.category === librechatDataProvider.SystemCategories.NO_CATEGORY) {
                query.category = '';
            }
            else if (query.category === librechatDataProvider.SystemCategories.SHARED_PROMPTS) {
                delete query.category;
            }
            const skip = (validatedPageNumber - 1) * validatedPageSize;
            const limit = validatedPageSize;
            const [groups, totalPromptGroups] = await Promise.all([
                PromptGroup.find(query)
                    .sort({ numberOfGenerations: -1, updatedAt: -1, _id: 1 })
                    .skip(skip)
                    .limit(limit)
                    .select('name numberOfGenerations oneliner category productionId author authorName createdAt updatedAt')
                    .lean(),
                PromptGroup.countDocuments(query),
            ]);
            const promptGroups = await attachProductionPrompts(groups);
            return {
                promptGroups,
                pageNumber: validatedPageNumber.toString(),
                pageSize: validatedPageSize.toString(),
                pages: Math.ceil(totalPromptGroups / validatedPageSize).toString(),
            };
        }
        catch (error) {
            winston.error('Error getting prompt groups', error);
            return { message: 'Error getting prompt groups' };
        }
    }
    /**
     * Delete a prompt group and its prompts, cleaning up ACL permissions.
     *
     * **Authorization is enforced upstream.** This method performs no ownership
     * check — it deletes any group by ID. Callers must gate access via
     * `canAccessPromptGroupResource` middleware before invoking this.
     */
    async function deletePromptGroup({ _id }) {
        const PromptGroup = mongoose.models.PromptGroup;
        const Prompt = mongoose.models.Prompt;
        const query = { _id };
        const groupQuery = { groupId: new ObjectId(_id) };
        const response = await PromptGroup.deleteOne(query);
        if (!response || response.deletedCount === 0) {
            throw new Error('Prompt group not found');
        }
        await Prompt.deleteMany(groupQuery);
        try {
            await deps.removeAllPermissions({
                resourceType: librechatDataProvider.ResourceType.PROMPTGROUP,
                resourceId: _id,
            });
        }
        catch (error) {
            winston.error('Error removing promptGroup permissions:', error);
        }
        return { message: 'Prompt group deleted successfully' };
    }
    /**
     * Get prompt groups by accessible IDs with optional cursor-based pagination.
     */
    async function getListPromptGroupsByAccess({ accessibleIds = [], otherParams = {}, limit = null, after = null, }) {
        const PromptGroup = mongoose.models.PromptGroup;
        const isPaginated = limit !== null && limit !== undefined;
        const normalizedLimit = isPaginated
            ? Math.min(Math.max(1, parseInt(String(limit)) || 20), 100)
            : null;
        const baseQuery = {
            ...otherParams,
            _id: { $in: accessibleIds },
        };
        let matchQuery = baseQuery;
        if (after && typeof after === 'string' && after !== 'undefined' && after !== 'null') {
            try {
                const cursor = JSON.parse(Buffer.from(after, 'base64').toString('utf8'));
                const { numberOfGenerations = 0, updatedAt, _id } = cursor;
                if (typeof numberOfGenerations !== 'number' ||
                    !Number.isFinite(numberOfGenerations) ||
                    typeof updatedAt !== 'string' ||
                    Number.isNaN(new Date(updatedAt).getTime()) ||
                    typeof _id !== 'string' ||
                    !objectId.isValidObjectIdString(_id)) {
                    winston.warn('[getListPromptGroupsByAccess] Invalid cursor fields, skipping cursor condition');
                }
                else {
                    const cursorCondition = {
                        $or: [
                            { numberOfGenerations: { $lt: numberOfGenerations } },
                            {
                                numberOfGenerations,
                                updatedAt: { $lt: new Date(updatedAt) },
                            },
                            {
                                numberOfGenerations,
                                updatedAt: new Date(updatedAt),
                                _id: { $gt: new ObjectId(_id) },
                            },
                        ],
                    };
                    matchQuery =
                        Object.keys(baseQuery).length > 0
                            ? { $and: [baseQuery, cursorCondition] }
                            : cursorCondition;
                }
            }
            catch (error) {
                winston.warn('Invalid cursor:', error.message);
            }
        }
        const findQuery = PromptGroup.find(matchQuery)
            .sort({ numberOfGenerations: -1, updatedAt: -1, _id: 1 })
            .select('name numberOfGenerations oneliner category productionId author authorName createdAt updatedAt');
        if (isPaginated && normalizedLimit) {
            findQuery.limit(normalizedLimit + 1);
        }
        const groups = await findQuery.lean();
        const promptGroups = await attachProductionPrompts(groups);
        const hasMore = isPaginated && normalizedLimit ? promptGroups.length > normalizedLimit : false;
        const data = (isPaginated && normalizedLimit ? promptGroups.slice(0, normalizedLimit) : promptGroups).map((group) => {
            if (group.author) {
                group.author = group.author.toString();
            }
            return group;
        });
        let nextCursor = null;
        if (isPaginated && hasMore && data.length > 0 && normalizedLimit) {
            const lastGroup = promptGroups[normalizedLimit - 1];
            nextCursor = Buffer.from(JSON.stringify({
                numberOfGenerations: lastGroup.numberOfGenerations,
                updatedAt: lastGroup.updatedAt.toISOString(),
                _id: lastGroup._id.toString(),
            })).toString('base64');
        }
        return {
            object: 'list',
            data,
            first_id: data.length > 0 ? data[0]._id.toString() : null,
            last_id: data.length > 0 ? data[data.length - 1]._id.toString() : null,
            has_more: hasMore,
            after: nextCursor,
        };
    }
    /**
     * Increment the numberOfGenerations counter for a prompt group.
     */
    async function incrementPromptGroupUsage(groupId) {
        if (!objectId.isValidObjectIdString(groupId)) {
            throw new Error('Invalid groupId');
        }
        const PromptGroup = mongoose.models.PromptGroup;
        const result = await PromptGroup.findByIdAndUpdate(groupId, { $inc: { numberOfGenerations: 1 } }, { new: true, select: 'numberOfGenerations' }).lean();
        if (!result) {
            throw new Error('Prompt group not found');
        }
        return { numberOfGenerations: result.numberOfGenerations };
    }
    /**
     * Create a prompt and its respective group.
     */
    async function createPromptGroup(saveData) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            const Prompt = mongoose.models.Prompt;
            const { prompt, group, author, authorName } = saveData;
            let newPromptGroup = await PromptGroup.findOneAndUpdate({ ...group, author, authorName, productionId: null }, { $setOnInsert: { ...group, author, authorName, productionId: null } }, { new: true, upsert: true })
                .lean()
                .select('-__v')
                .exec();
            const newPrompt = await Prompt.findOneAndUpdate({ ...prompt, author, groupId: newPromptGroup._id }, { $setOnInsert: { ...prompt, author, groupId: newPromptGroup._id } }, { new: true, upsert: true })
                .lean()
                .select('-__v')
                .exec();
            newPromptGroup = (await PromptGroup.findByIdAndUpdate(newPromptGroup._id, { productionId: newPrompt._id }, { new: true })
                .lean()
                .select('-__v')
                .exec());
            return {
                prompt: newPrompt,
                group: {
                    ...newPromptGroup,
                    productionPrompt: { prompt: newPrompt.prompt },
                },
            };
        }
        catch (error) {
            winston.error('Error saving prompt group', error);
            throw new Error('Error saving prompt group');
        }
    }
    /**
     * Save a prompt.
     */
    async function savePrompt(saveData) {
        var _a;
        try {
            const Prompt = mongoose.models.Prompt;
            const { prompt, author } = saveData;
            const newPromptData = { ...prompt, author };
            let newPrompt;
            try {
                newPrompt = await Prompt.create(newPromptData);
            }
            catch (error) {
                if ((_a = error === null || error === void 0 ? void 0 : error.message) === null || _a === void 0 ? void 0 : _a.includes('groupId_1_version_1')) {
                    await Prompt.db.collection('prompts').dropIndex('groupId_1_version_1');
                }
                else {
                    throw error;
                }
                newPrompt = await Prompt.create(newPromptData);
            }
            return { prompt: newPrompt };
        }
        catch (error) {
            winston.error('Error saving prompt', error);
            return { message: 'Error saving prompt' };
        }
    }
    /**
     * Get prompts by filter.
     */
    async function getPrompts(filter) {
        try {
            const Prompt = mongoose.models.Prompt;
            return await Prompt.find(filter).sort({ createdAt: -1 }).lean();
        }
        catch (error) {
            winston.error('Error getting prompts', error);
            return { message: 'Error getting prompts' };
        }
    }
    /**
     * Get a single prompt by filter.
     */
    async function getPrompt(filter) {
        try {
            const Prompt = mongoose.models.Prompt;
            if (filter.groupId) {
                filter.groupId = new ObjectId(filter.groupId);
            }
            return await Prompt.findOne(filter).lean();
        }
        catch (error) {
            winston.error('Error getting prompt', error);
            return { message: 'Error getting prompt' };
        }
    }
    /**
     * Get random prompt groups from distinct categories.
     */
    async function getRandomPromptGroups(filter) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            const categories = await PromptGroup.distinct('category', { category: { $ne: '' } });
            for (let i = categories.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [categories[i], categories[j]] = [categories[j], categories[i]];
            }
            const skip = +filter.skip;
            const limit = +filter.limit;
            const selectedCategories = categories.slice(skip, skip + limit);
            if (selectedCategories.length === 0) {
                return { prompts: [] };
            }
            const groups = await PromptGroup.find({ category: { $in: selectedCategories } }).lean();
            const groupByCategory = new Map();
            for (const group of groups) {
                if (!groupByCategory.has(group.category)) {
                    groupByCategory.set(group.category, group);
                }
            }
            const prompts = selectedCategories
                .map((cat) => groupByCategory.get(cat))
                .filter(Boolean);
            return { prompts };
        }
        catch (error) {
            winston.error('Error getting prompt groups', error);
            return { message: 'Error getting prompt groups' };
        }
    }
    /**
     * Get prompt groups with populated prompts.
     */
    async function getPromptGroupsWithPrompts(filter) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            return await PromptGroup.findOne(filter)
                .populate({
                path: 'prompts',
                select: '-_id -__v -user',
            })
                .select('-_id -__v -user')
                .lean();
        }
        catch (error) {
            winston.error('Error getting prompt groups', error);
            return { message: 'Error getting prompt groups' };
        }
    }
    /**
     * Get a single prompt group by filter, with productionPrompt populated via $lookup.
     */
    async function getPromptGroup(filter) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            // Cast string _id to ObjectId for aggregation (findOne auto-casts, aggregate does not)
            const matchFilter = { ...filter };
            if (typeof matchFilter._id === 'string') {
                matchFilter._id = new ObjectId(matchFilter._id);
            }
            const tenantId = tenantContext.getTenantId();
            const useTenantFilter = tenantId && tenantId !== tenantContext.SYSTEM_TENANT_ID;
            const result = await PromptGroup.aggregate([
                { $match: matchFilter },
                {
                    $lookup: {
                        from: 'prompts',
                        localField: 'productionId',
                        foreignField: '_id',
                        as: 'productionPrompt',
                    },
                },
                { $unwind: { path: '$productionPrompt', preserveNullAndEmptyArrays: true } },
            ]);
            const group = result[0] || null;
            if ((group === null || group === void 0 ? void 0 : group.productionPrompt) &&
                useTenantFilter &&
                group.productionPrompt.tenantId !== tenantId) {
                group.productionPrompt = null;
            }
            if (group === null || group === void 0 ? void 0 : group.author) {
                group.author = group.author.toString();
            }
            return group;
        }
        catch (error) {
            winston.error('Error getting prompt group', error);
            return null;
        }
    }
    /**
     * Returns the _id values of all prompt groups authored by the given user.
     * Used by the "Shared Prompts" and "My Prompts" filters to distinguish
     * owned prompts from prompts shared with the user.
     */
    async function getOwnedPromptGroupIds(author) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            if (!author || !ObjectId.isValid(author)) {
                winston.warn('getOwnedPromptGroupIds called with invalid author', { author });
                return [];
            }
            const groups = await PromptGroup.find({ author: new ObjectId(author) }, { _id: 1 }).lean();
            return groups.map((g) => g._id);
        }
        catch (error) {
            winston.error('Error getting owned prompt group IDs', error);
            return [];
        }
    }
    /**
     * Delete a prompt, potentially removing the group if it's the last prompt.
     *
     * **Authorization is enforced upstream.** This method performs no ownership
     * check — it deletes any prompt by ID. Callers must gate access via
     * `canAccessPromptViaGroup` middleware before invoking this.
     */
    async function deletePrompt({ promptId, groupId, }) {
        var _a;
        const Prompt = mongoose.models.Prompt;
        const PromptGroup = mongoose.models.PromptGroup;
        const query = { _id: promptId, groupId };
        const { deletedCount } = await Prompt.deleteOne(query);
        if (deletedCount === 0) {
            throw new Error('Failed to delete the prompt');
        }
        const remainingPrompts = await Prompt.find({ groupId })
            .select('_id')
            .sort({ createdAt: 1 })
            .lean();
        if (remainingPrompts.length === 0) {
            try {
                await deps.removeAllPermissions({
                    resourceType: librechatDataProvider.ResourceType.PROMPTGROUP,
                    resourceId: groupId,
                });
            }
            catch (error) {
                winston.error('Error removing promptGroup permissions:', error);
            }
            await PromptGroup.deleteOne({ _id: groupId });
            return {
                prompt: 'Prompt deleted successfully',
                promptGroup: {
                    message: 'Prompt group deleted successfully',
                    id: groupId,
                },
            };
        }
        else {
            const promptGroup = (await PromptGroup.findById(groupId).lean());
            if (promptGroup && ((_a = promptGroup.productionId) === null || _a === void 0 ? void 0 : _a.toString()) === promptId.toString()) {
                await PromptGroup.updateOne({ _id: groupId }, { productionId: remainingPrompts[remainingPrompts.length - 1]._id });
            }
            return { prompt: 'Prompt deleted successfully' };
        }
    }
    /**
     * Delete all prompts and prompt groups created by a specific user.
     */
    /**
     * Deletes prompt groups solely owned by the user and cleans up their prompts/ACLs.
     * Groups with other owners are left intact; the caller is responsible for
     * removing the user's own ACL principal entries separately.
     *
     * Also handles legacy (pre-ACL) prompt groups that only have the author field set,
     * ensuring they are not orphaned if the permission migration has not been run.
     */
    async function deleteUserPrompts(userId) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            const Prompt = mongoose.models.Prompt;
            const AclEntry = mongoose.models.AclEntry;
            const userObjectId = new ObjectId(userId);
            const soleOwnedIds = await getSoleOwnedResourceIds(userObjectId, librechatDataProvider.ResourceType.PROMPTGROUP);
            const authoredGroups = await PromptGroup.find({ author: userObjectId }).select('_id').lean();
            const authoredGroupIds = authoredGroups.map((g) => g._id);
            const migratedEntries = authoredGroupIds.length > 0
                ? await AclEntry.find({
                    resourceType: librechatDataProvider.ResourceType.PROMPTGROUP,
                    resourceId: { $in: authoredGroupIds },
                })
                    .select('resourceId')
                    .lean()
                : [];
            const migratedIds = new Set(migratedEntries.map((e) => e.resourceId.toString()));
            const legacyGroupIds = authoredGroupIds.filter((id) => !migratedIds.has(id.toString()));
            const allGroupIdsToDelete = [...soleOwnedIds, ...legacyGroupIds];
            if (allGroupIdsToDelete.length === 0) {
                return;
            }
            await AclEntry.deleteMany({
                resourceType: librechatDataProvider.ResourceType.PROMPTGROUP,
                resourceId: { $in: allGroupIdsToDelete },
            });
            await PromptGroup.deleteMany({ _id: { $in: allGroupIdsToDelete } });
            await Prompt.deleteMany({ groupId: { $in: allGroupIdsToDelete } });
        }
        catch (error) {
            winston.error('[deleteUserPrompts] General error:', error);
        }
    }
    /**
     * Update a prompt group.
     */
    async function updatePromptGroup(filter, data) {
        try {
            const PromptGroup = mongoose.models.PromptGroup;
            const updateOps = {};
            const updateData = { ...data, ...updateOps };
            const updatedDoc = await PromptGroup.findOneAndUpdate(filter, updateData, {
                new: true,
                upsert: false,
            });
            if (!updatedDoc) {
                throw new Error('Prompt group not found');
            }
            return updatedDoc;
        }
        catch (error) {
            winston.error('Error updating prompt group', error);
            return { message: 'Error updating prompt group' };
        }
    }
    /**
     * Make a prompt the production prompt for its group.
     */
    async function makePromptProduction(promptId) {
        try {
            const Prompt = mongoose.models.Prompt;
            const PromptGroup = mongoose.models.PromptGroup;
            const prompt = await Prompt.findById(promptId).lean();
            if (!prompt) {
                throw new Error('Prompt not found');
            }
            await PromptGroup.findByIdAndUpdate(prompt.groupId, { productionId: prompt._id }, { new: true })
                .lean()
                .exec();
            return { message: 'Prompt production made successfully' };
        }
        catch (error) {
            winston.error('Error making prompt production', error);
            return { message: 'Error making prompt production' };
        }
    }
    /**
     * Update prompt labels.
     */
    async function updatePromptLabels(_id, labels) {
        try {
            const Prompt = mongoose.models.Prompt;
            const response = await Prompt.updateOne({ _id }, { $set: { labels } });
            if (response.matchedCount === 0) {
                return { message: 'Prompt not found' };
            }
            return { message: 'Prompt labels updated successfully' };
        }
        catch (error) {
            winston.error('Error updating prompt labels', error);
            return { message: 'Error updating prompt labels' };
        }
    }
    return {
        getPromptGroups,
        deletePromptGroup,
        getAllPromptGroups,
        getListPromptGroupsByAccess,
        incrementPromptGroupUsage,
        createPromptGroup,
        savePrompt,
        getPrompts,
        getPrompt,
        getRandomPromptGroups,
        getPromptGroupsWithPrompts,
        getPromptGroup,
        getOwnedPromptGroupIds,
        deletePrompt,
        deleteUserPrompts,
        updatePromptGroup,
        makePromptProduction,
        updatePromptLabels,
    };
}

exports.createPromptMethods = createPromptMethods;
//# sourceMappingURL=prompt.cjs.map
