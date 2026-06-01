'use strict';

const sensitiveFields = ['api_key', 'oauth_client_id', 'oauth_client_secret'];
function createActionMethods(mongoose) {
    /**
     * Update an action with new data without overwriting existing properties,
     * or create a new action if it doesn't exist.
     */
    async function updateAction(searchParams, updateData) {
        const Action = mongoose.models.Action;
        const options = { new: true, upsert: true };
        return await Action.findOneAndUpdate(searchParams, updateData, options).lean();
    }
    /**
     * Retrieves all actions that match the given search parameters.
     */
    async function getActions(searchParams, includeSensitive = false) {
        const Action = mongoose.models.Action;
        const actions = await Action.find(searchParams).lean();
        if (!includeSensitive) {
            for (let i = 0; i < actions.length; i++) {
                const metadata = actions[i].metadata;
                if (!metadata) {
                    continue;
                }
                for (const field of sensitiveFields) {
                    if (metadata[field]) {
                        delete metadata[field];
                    }
                }
            }
        }
        return actions;
    }
    /**
     * Deletes an action by params.
     */
    async function deleteAction(searchParams) {
        const Action = mongoose.models.Action;
        return await Action.findOneAndDelete(searchParams).lean();
    }
    /**
     * Deletes actions by params.
     */
    async function deleteActions(searchParams) {
        const Action = mongoose.models.Action;
        const result = await Action.deleteMany(searchParams);
        return result.deletedCount;
    }
    return {
        getActions,
        updateAction,
        deleteAction,
        deleteActions,
    };
}

exports.createActionMethods = createActionMethods;
//# sourceMappingURL=action.cjs.map
