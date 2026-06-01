// Factory function that takes mongoose instance and returns the methods
function createPluginAuthMethods(mongoose) {
    /**
     * Finds a single plugin auth entry by userId and authField (and optionally pluginKey)
     */
    async function findOnePluginAuth({ userId, authField, pluginKey, }) {
        try {
            const PluginAuth = mongoose.models.PluginAuth;
            return await PluginAuth.findOne({
                userId,
                authField,
                ...(pluginKey && { pluginKey }),
            }).lean();
        }
        catch (error) {
            throw new Error(`Failed to find plugin auth: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
    /**
     * Finds multiple plugin auth entries by userId and pluginKeys
     */
    async function findPluginAuthsByKeys({ userId, pluginKeys, }) {
        try {
            if (!pluginKeys || pluginKeys.length === 0) {
                return [];
            }
            const PluginAuth = mongoose.models.PluginAuth;
            return await PluginAuth.find({
                userId,
                pluginKey: { $in: pluginKeys },
            }).lean();
        }
        catch (error) {
            throw new Error(`Failed to find plugin auths: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
    /**
     * Updates or creates a plugin auth entry
     */
    async function updatePluginAuth({ userId, authField, pluginKey, value, }) {
        try {
            const PluginAuth = mongoose.models.PluginAuth;
            const existingAuth = await PluginAuth.findOne({
                userId,
                pluginKey,
                authField,
            }).lean();
            if (existingAuth) {
                return await PluginAuth.findOneAndUpdate({ userId, pluginKey, authField }, { $set: { value } }, { new: true, upsert: true }).lean();
            }
            else {
                const newPluginAuth = await new PluginAuth({
                    userId,
                    authField,
                    value,
                    pluginKey,
                });
                await newPluginAuth.save();
                return newPluginAuth.toObject();
            }
        }
        catch (error) {
            throw new Error(`Failed to update plugin auth: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
    /**
     * Deletes plugin auth entries based on provided parameters
     */
    async function deletePluginAuth({ userId, authField, pluginKey, all = false, }) {
        try {
            const PluginAuth = mongoose.models.PluginAuth;
            if (all) {
                const filter = { userId };
                if (pluginKey) {
                    filter.pluginKey = pluginKey;
                }
                return await PluginAuth.deleteMany(filter);
            }
            if (!authField) {
                throw new Error('authField is required when all is false');
            }
            return await PluginAuth.deleteOne({ userId, authField });
        }
        catch (error) {
            throw new Error(`Failed to delete plugin auth: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
    /**
     * Deletes all plugin auth entries for a user
     */
    async function deleteAllUserPluginAuths(userId) {
        try {
            const PluginAuth = mongoose.models.PluginAuth;
            return await PluginAuth.deleteMany({ userId });
        }
        catch (error) {
            throw new Error(`Failed to delete all user plugin auths: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
    return {
        findOnePluginAuth,
        findPluginAuthsByKeys,
        updatePluginAuth,
        deletePluginAuth,
        deleteAllUserPluginAuths,
    };
}

export { createPluginAuthMethods };
//# sourceMappingURL=pluginAuth.es.js.map
