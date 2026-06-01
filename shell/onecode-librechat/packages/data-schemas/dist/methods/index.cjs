'use strict';

var session = require('./session.cjs');
var token = require('./token.cjs');
var role = require('./role.cjs');
var user = require('./user.cjs');
var key = require('./key.cjs');
var file = require('./file.cjs');
var memory = require('./memory.cjs');
var agentCategory = require('./agentCategory.cjs');
var agentApiKey = require('./agentApiKey.cjs');
var mcpServer = require('./mcpServer.cjs');
var pluginAuth = require('./pluginAuth.cjs');
var accessRole = require('./accessRole.cjs');
var userGroup = require('./userGroup.cjs');
var aclEntry = require('./aclEntry.cjs');
var systemGrant = require('./systemGrant.cjs');
var share = require('./share.cjs');
var action = require('./action.cjs');
var assistant = require('./assistant.cjs');
var banner = require('./banner.cjs');
var toolCall = require('./toolCall.cjs');
var categories = require('./categories.cjs');
var preset = require('./preset.cjs');
var conversationTag = require('./conversationTag.cjs');
var message = require('./message.cjs');
var conversation = require('./conversation.cjs');
var tx = require('./tx.cjs');
var transaction = require('./transaction.cjs');
var spendTokens = require('./spendTokens.cjs');
var prompt = require('./prompt.cjs');
var skill = require('./skill.cjs');
var agent = require('./agent.cjs');
var config = require('./config.cjs');

/**
 * Creates all database methods for all collections
 * @param mongoose - Mongoose instance
 * @param deps - Optional dependencies injected from the api layer
 */
function createMethods(mongoose, deps = {}) {
    var _a, _b, _c;
    // Tier 3: tx methods need matchModelName and findMatchingPattern
    const txDeps = {
        matchModelName: (_a = deps.matchModelName) !== null && _a !== void 0 ? _a : (() => undefined),
        findMatchingPattern: (_b = deps.findMatchingPattern) !== null && _b !== void 0 ? _b : (() => undefined),
    };
    const txMethods = tx.createTxMethods(mongoose, txDeps);
    // Tier 3: transaction methods need tx's getMultiplier/getCacheMultiplier
    const transactionMethods = transaction.createTransactionMethods(mongoose, {
        getMultiplier: txMethods.getMultiplier,
        getCacheMultiplier: txMethods.getCacheMultiplier,
    });
    // Tier 3: spendTokens methods need transaction methods
    const spendTokensMethods = spendTokens.createSpendTokensMethods(mongoose, {
        createTransaction: transactionMethods.createTransaction,
        createStructuredTransaction: transactionMethods.createStructuredTransaction,
    });
    const messageMethods = message.createMessageMethods(mongoose);
    const conversationMethods = conversation.createConversationMethods(mongoose, {
        getMessages: messageMethods.getMessages,
        deleteMessages: messageMethods.deleteMessages,
    });
    // ACL entry methods (used internally for removeAllPermissions)
    const aclEntryMethods = aclEntry.createAclEntryMethods(mongoose);
    const systemGrantMethods = systemGrant.createSystemGrantMethods(mongoose);
    // Internal removeAllPermissions: use deleteAclEntries from aclEntryMethods
    // instead of requiring it as an external dep from PermissionService
    const removeAllPermissions = (_c = deps.removeAllPermissions) !== null && _c !== void 0 ? _c : (async ({ resourceType, resourceId }) => {
        await aclEntryMethods.deleteAclEntries({ resourceType, resourceId });
    });
    const promptDeps = {
        removeAllPermissions,
        getSoleOwnedResourceIds: aclEntryMethods.getSoleOwnedResourceIds,
    };
    const promptMethods = prompt.createPromptMethods(mongoose, promptDeps);
    const skillDeps = {
        removeAllPermissions,
        getSoleOwnedResourceIds: aclEntryMethods.getSoleOwnedResourceIds,
    };
    const skillMethods = skill.createSkillMethods(mongoose, skillDeps);
    // Role methods with optional cache injection
    const roleDeps = { getCache: deps.getCache };
    const roleMethods = role.createRoleMethods(mongoose, roleDeps);
    // Tier 1: action methods (created as variable for agent dependency)
    const actionMethods = action.createActionMethods(mongoose);
    // Tier 5: agent methods need removeAllPermissions + getActions
    const agentDeps = {
        removeAllPermissions,
        getActions: actionMethods.getActions,
        getSoleOwnedResourceIds: aclEntryMethods.getSoleOwnedResourceIds,
    };
    const agentMethods = agent.createAgentMethods(mongoose, agentDeps);
    return {
        ...user.createUserMethods(mongoose),
        ...session.createSessionMethods(mongoose),
        ...token.createTokenMethods(mongoose),
        ...roleMethods,
        ...key.createKeyMethods(mongoose),
        ...file.createFileMethods(mongoose),
        ...memory.createMemoryMethods(mongoose),
        ...agentCategory.createAgentCategoryMethods(mongoose),
        ...agentApiKey.createAgentApiKeyMethods(mongoose),
        ...mcpServer.createMCPServerMethods(mongoose),
        ...accessRole.createAccessRoleMethods(mongoose),
        ...userGroup.createUserGroupMethods(mongoose),
        ...aclEntryMethods,
        ...systemGrantMethods,
        ...share.createShareMethods(mongoose),
        ...pluginAuth.createPluginAuthMethods(mongoose),
        /* Tier 1 */
        ...actionMethods,
        ...assistant.createAssistantMethods(mongoose),
        ...banner.createBannerMethods(mongoose),
        ...toolCall.createToolCallMethods(mongoose),
        ...categories.createCategoriesMethods(),
        ...preset.createPresetMethods(mongoose),
        /* Tier 2 */
        ...conversationTag.createConversationTagMethods(mongoose),
        ...messageMethods,
        ...conversationMethods,
        /* Tier 3 */
        ...txMethods,
        ...transactionMethods,
        ...spendTokensMethods,
        ...promptMethods,
        ...skillMethods,
        /* Tier 5 */
        ...agentMethods,
        /* Config */
        ...config.createConfigMethods(mongoose),
    };
}

exports.DEFAULT_REFRESH_TOKEN_EXPIRY = session.DEFAULT_REFRESH_TOKEN_EXPIRY;
exports.RoleConflictError = role.RoleConflictError;
exports.DEFAULT_SESSION_EXPIRY = user.DEFAULT_SESSION_EXPIRY;
exports.permissionBitSupersets = aclEntry.permissionBitSupersets;
exports.cacheTokenValues = tx.cacheTokenValues;
exports.defaultRate = tx.defaultRate;
exports.premiumTokenValues = tx.premiumTokenValues;
exports.tokenValues = tx.tokenValues;
exports.createMethods = createMethods;
//# sourceMappingURL=index.cjs.map
