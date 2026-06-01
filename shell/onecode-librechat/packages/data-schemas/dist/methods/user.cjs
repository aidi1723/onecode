'use strict';

var string = require('../utils/string.cjs');
var index = require('../crypto/index.cjs');

/** Default JWT session expiry: 15 minutes in milliseconds */
const DEFAULT_SESSION_EXPIRY = 1000 * 60 * 15;
/** Factory function that takes mongoose instance and returns the methods */
function createUserMethods(mongoose) {
    /**
     * Normalizes email fields in search criteria to lowercase and trimmed.
     * Handles both direct email fields and $or arrays containing email conditions.
     */
    function normalizeEmailInCriteria(criteria) {
        const normalized = { ...criteria };
        if (typeof normalized.email === 'string') {
            normalized.email = normalized.email.trim().toLowerCase();
        }
        if (Array.isArray(normalized.$or)) {
            normalized.$or = normalized.$or.map((condition) => {
                if (typeof condition.email === 'string') {
                    return { ...condition, email: condition.email.trim().toLowerCase() };
                }
                return condition;
            });
        }
        return normalized;
    }
    /**
     * Search for a single user based on partial data and return matching user document as plain object.
     * Email fields in searchCriteria are automatically normalized to lowercase for case-insensitive matching.
     */
    async function findUser(searchCriteria, fieldsToSelect) {
        const User = mongoose.models.User;
        const normalizedCriteria = normalizeEmailInCriteria(searchCriteria);
        const query = User.findOne(normalizedCriteria);
        if (fieldsToSelect) {
            query.select(fieldsToSelect);
        }
        return await query.lean();
    }
    async function findUsers(searchCriteria, fieldsToSelect, options) {
        const User = mongoose.models.User;
        const normalizedCriteria = normalizeEmailInCriteria(searchCriteria);
        const query = User.find(normalizedCriteria);
        if (fieldsToSelect) {
            query.select(fieldsToSelect);
        }
        if ((options === null || options === void 0 ? void 0 : options.sort) != null) {
            query.sort(options.sort);
        }
        if ((options === null || options === void 0 ? void 0 : options.offset) != null) {
            query.skip(options.offset);
        }
        if ((options === null || options === void 0 ? void 0 : options.limit) != null && options.limit > 0) {
            query.limit(options.limit);
        }
        return await query.lean();
    }
    /**
     * Count the number of user documents in the collection based on the provided filter.
     */
    async function countUsers(filter = {}) {
        const User = mongoose.models.User;
        return await User.countDocuments(filter);
    }
    /**
     * Creates a new user, optionally with a TTL of 1 week.
     */
    async function createUser(data, balanceConfig, disableTTL = true, returnUser = false) {
        const User = mongoose.models.User;
        const Balance = mongoose.models.Balance;
        const userData = {
            ...data,
            expiresAt: disableTTL ? undefined : new Date(Date.now() + 604800 * 1000), // 1 week in milliseconds
        };
        if (disableTTL) {
            delete userData.expiresAt;
        }
        const user = await User.create(userData);
        // If balance is enabled, create or update a balance record for the user
        if ((balanceConfig === null || balanceConfig === void 0 ? void 0 : balanceConfig.enabled) && (balanceConfig === null || balanceConfig === void 0 ? void 0 : balanceConfig.startBalance)) {
            const update = {
                $inc: { tokenCredits: balanceConfig.startBalance },
            };
            if (balanceConfig.autoRefillEnabled &&
                balanceConfig.refillIntervalValue != null &&
                balanceConfig.refillIntervalUnit != null &&
                balanceConfig.refillAmount != null) {
                update.$set = {
                    autoRefillEnabled: true,
                    refillIntervalValue: balanceConfig.refillIntervalValue,
                    refillIntervalUnit: balanceConfig.refillIntervalUnit,
                    refillAmount: balanceConfig.refillAmount,
                };
            }
            await Balance.findOneAndUpdate({ user: user._id }, update, {
                upsert: true,
                new: true,
            }).lean();
        }
        if (returnUser) {
            return user.toObject();
        }
        return user._id;
    }
    /**
     * Update a user with new data without overwriting existing properties.
     */
    async function updateUser(userId, updateData) {
        const User = mongoose.models.User;
        const updateOperation = {
            $set: updateData,
            $unset: { expiresAt: '' }, // Remove the expiresAt field to prevent TTL
        };
        return await User.findByIdAndUpdate(userId, updateOperation, {
            new: true,
            runValidators: true,
        }).lean();
    }
    /**
     * Retrieve a user by ID and convert the found user document to a plain object.
     */
    async function getUserById(userId, fieldsToSelect) {
        const User = mongoose.models.User;
        const query = User.findById(userId);
        if (fieldsToSelect) {
            query.select(fieldsToSelect);
        }
        return await query.lean();
    }
    /**
     * Delete a user by their unique ID.
     */
    async function deleteUserById(userId) {
        try {
            const User = mongoose.models.User;
            const result = await User.deleteOne({ _id: userId });
            if (result.deletedCount === 0) {
                return { deletedCount: 0, message: 'No user found with that ID.' };
            }
            return { deletedCount: result.deletedCount, message: 'User was deleted successfully.' };
        }
        catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            throw new Error('Error deleting user: ' + errorMessage);
        }
    }
    /**
     * Generates a JWT token for a given user.
     * @param user - The user object
     * @param expiresIn - Optional expiry time in milliseconds. Default: 15 minutes
     */
    async function generateToken(user, expiresIn) {
        if (!user) {
            throw new Error('No user provided');
        }
        const expires = expiresIn !== null && expiresIn !== void 0 ? expiresIn : DEFAULT_SESSION_EXPIRY;
        return await index.signPayload({
            payload: {
                id: user._id,
                username: user.username,
                provider: user.provider,
                email: user.email,
            },
            secret: process.env.JWT_SECRET,
            expirationTime: expires / 1000,
        });
    }
    /**
     * Update a user's personalization memories setting.
     * Handles the edge case where the personalization object doesn't exist.
     */
    async function toggleUserMemories(userId, memoriesEnabled) {
        const User = mongoose.models.User;
        // First, ensure the personalization object exists
        const user = await User.findById(userId);
        if (!user) {
            return null;
        }
        // Use $set to update the nested field, which will create the personalization object if it doesn't exist
        const updateOperation = {
            $set: {
                'personalization.memories': memoriesEnabled,
            },
        };
        return await User.findByIdAndUpdate(userId, updateOperation, {
            new: true,
            runValidators: true,
        }).lean();
    }
    /**
     * Search for users by pattern matching on name, email, or username (case-insensitive)
     * @param searchPattern - The pattern to search for
     * @param limit - Maximum number of results to return
     * @param fieldsToSelect - The fields to include or exclude in the returned documents
     * @returns Array of matching user documents
     */
    const searchUsers = async function ({ searchPattern, limit = 20, fieldsToSelect = null, }) {
        if (!searchPattern || searchPattern.trim().length === 0) {
            return [];
        }
        const trimmedPattern = searchPattern.trim();
        const regex = new RegExp(string.escapeRegExp(trimmedPattern), 'i');
        const User = mongoose.models.User;
        const query = User.find({
            $or: [{ email: regex }, { name: regex }, { username: regex }],
        }).limit(limit * 2); // Get more results to allow for relevance sorting
        if (fieldsToSelect) {
            query.select(fieldsToSelect);
        }
        const users = await query.lean();
        // Score results by relevance
        const startsWithPattern = trimmedPattern.toLowerCase();
        const scoredUsers = users.map((user) => {
            const searchableFields = [user.name, user.email, user.username].filter((field) => typeof field === 'string' && field.length > 0);
            let maxScore = 0;
            for (const field of searchableFields) {
                const fieldLower = field.toLowerCase();
                let score = 0;
                // Exact match gets highest score
                if (fieldLower === startsWithPattern) {
                    score = 100;
                }
                // Starts with query gets high score
                else if (fieldLower.startsWith(startsWithPattern)) {
                    score = 80;
                }
                // Contains query gets medium score
                else if (fieldLower.includes(startsWithPattern)) {
                    score = 50;
                }
                // Default score for database match
                else {
                    score = 10;
                }
                maxScore = Math.max(maxScore, score);
            }
            return { ...user, _searchScore: maxScore };
        });
        /** Top results sorted by relevance */
        return scoredUsers
            .sort((a, b) => b._searchScore - a._searchScore)
            .slice(0, limit)
            .map((user) => {
            const { _searchScore, ...userWithoutScore } = user;
            return userWithoutScore;
        });
    };
    /**
     * Updates the plugins for a user based on the action specified (install/uninstall).
     * @param userId - The user ID whose plugins are to be updated
     * @param plugins - The current plugins array
     * @param pluginKey - The key of the plugin to install or uninstall
     * @param action - The action to perform, 'install' or 'uninstall'
     * @returns The result of the update operation or null if action is invalid
     */
    async function updateUserPlugins(userId, plugins, pluginKey, action) {
        const userPlugins = plugins !== null && plugins !== void 0 ? plugins : [];
        if (action === 'install') {
            return updateUser(userId, { plugins: [...userPlugins, pluginKey] });
        }
        if (action === 'uninstall') {
            return updateUser(userId, {
                plugins: userPlugins.filter((plugin) => plugin !== pluginKey),
            });
        }
        return null;
    }
    return {
        findUser,
        findUsers,
        countUsers,
        createUser,
        updateUser,
        searchUsers,
        getUserById,
        generateToken,
        deleteUserById,
        updateUserPlugins,
        toggleUserMemories,
    };
}

exports.DEFAULT_SESSION_EXPIRY = DEFAULT_SESSION_EXPIRY;
exports.createUserMethods = createUserMethods;
//# sourceMappingURL=user.cjs.map
