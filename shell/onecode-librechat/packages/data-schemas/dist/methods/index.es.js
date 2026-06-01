import { createSessionMethods } from './session.es.js';
export { DEFAULT_REFRESH_TOKEN_EXPIRY } from './session.es.js';
import { createTokenMethods } from './token.es.js';
import { createRoleMethods } from './role.es.js';
export { RoleConflictError } from './role.es.js';
import { createUserMethods } from './user.es.js';
export { DEFAULT_SESSION_EXPIRY } from './user.es.js';
import { createKeyMethods } from './key.es.js';
import { createFileMethods } from './file.es.js';
import { createMemoryMethods } from './memory.es.js';
import { createAgentCategoryMethods } from './agentCategory.es.js';
import { createAgentApiKeyMethods } from './agentApiKey.es.js';
import { createMCPServerMethods } from './mcpServer.es.js';
import { createPluginAuthMethods } from './pluginAuth.es.js';
import { createAccessRoleMethods } from './accessRole.es.js';
import { createUserGroupMethods } from './userGroup.es.js';
import { createAclEntryMethods } from './aclEntry.es.js';
export { permissionBitSupersets } from './aclEntry.es.js';
import { createSystemGrantMethods } from './systemGrant.es.js';
import { createShareMethods } from './share.es.js';
import { createActionMethods } from './action.es.js';
import { createAssistantMethods } from './assistant.es.js';
import { createBannerMethods } from './banner.es.js';
import { createToolCallMethods } from './toolCall.es.js';
import { createCategoriesMethods } from './categories.es.js';
import { createPresetMethods } from './preset.es.js';
import { createConversationTagMethods } from './conversationTag.es.js';
import { createMessageMethods } from './message.es.js';
import { createConversationMethods } from './conversation.es.js';
import { createTxMethods } from './tx.es.js';
export { cacheTokenValues, defaultRate, premiumTokenValues, tokenValues } from './tx.es.js';
import { createTransactionMethods } from './transaction.es.js';
import { createSpendTokensMethods } from './spendTokens.es.js';
import { createPromptMethods } from './prompt.es.js';
import { createSkillMethods } from './skill.es.js';
import { createAgentMethods } from './agent.es.js';
import { createConfigMethods } from './config.es.js';

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
    const txMethods = createTxMethods(mongoose, txDeps);
    // Tier 3: transaction methods need tx's getMultiplier/getCacheMultiplier
    const transactionMethods = createTransactionMethods(mongoose, {
        getMultiplier: txMethods.getMultiplier,
        getCacheMultiplier: txMethods.getCacheMultiplier,
    });
    // Tier 3: spendTokens methods need transaction methods
    const spendTokensMethods = createSpendTokensMethods(mongoose, {
        createTransaction: transactionMethods.createTransaction,
        createStructuredTransaction: transactionMethods.createStructuredTransaction,
    });
    const messageMethods = createMessageMethods(mongoose);
    const conversationMethods = createConversationMethods(mongoose, {
        getMessages: messageMethods.getMessages,
        deleteMessages: messageMethods.deleteMessages,
    });
    // ACL entry methods (used internally for removeAllPermissions)
    const aclEntryMethods = createAclEntryMethods(mongoose);
    const systemGrantMethods = createSystemGrantMethods(mongoose);
    // Internal removeAllPermissions: use deleteAclEntries from aclEntryMethods
    // instead of requiring it as an external dep from PermissionService
    const removeAllPermissions = (_c = deps.removeAllPermissions) !== null && _c !== void 0 ? _c : (async ({ resourceType, resourceId }) => {
        await aclEntryMethods.deleteAclEntries({ resourceType, resourceId });
    });
    const promptDeps = {
        removeAllPermissions,
        getSoleOwnedResourceIds: aclEntryMethods.getSoleOwnedResourceIds,
    };
    const promptMethods = createPromptMethods(mongoose, promptDeps);
    const skillDeps = {
        removeAllPermissions,
        getSoleOwnedResourceIds: aclEntryMethods.getSoleOwnedResourceIds,
    };
    const skillMethods = createSkillMethods(mongoose, skillDeps);
    // Role methods with optional cache injection
    const roleDeps = { getCache: deps.getCache };
    const roleMethods = createRoleMethods(mongoose, roleDeps);
    // Tier 1: action methods (created as variable for agent dependency)
    const actionMethods = createActionMethods(mongoose);
    // Tier 5: agent methods need removeAllPermissions + getActions
    const agentDeps = {
        removeAllPermissions,
        getActions: actionMethods.getActions,
        getSoleOwnedResourceIds: aclEntryMethods.getSoleOwnedResourceIds,
    };
    const agentMethods = createAgentMethods(mongoose, agentDeps);
    return {
        ...createUserMethods(mongoose),
        ...createSessionMethods(mongoose),
        ...createTokenMethods(mongoose),
        ...roleMethods,
        ...createKeyMethods(mongoose),
        ...createFileMethods(mongoose),
        ...createMemoryMethods(mongoose),
        ...createAgentCategoryMethods(mongoose),
        ...createAgentApiKeyMethods(mongoose),
        ...createMCPServerMethods(mongoose),
        ...createAccessRoleMethods(mongoose),
        ...createUserGroupMethods(mongoose),
        ...aclEntryMethods,
        ...systemGrantMethods,
        ...createShareMethods(mongoose),
        ...createPluginAuthMethods(mongoose),
        /* Tier 1 */
        ...actionMethods,
        ...createAssistantMethods(mongoose),
        ...createBannerMethods(mongoose),
        ...createToolCallMethods(mongoose),
        ...createCategoriesMethods(),
        ...createPresetMethods(mongoose),
        /* Tier 2 */
        ...createConversationTagMethods(mongoose),
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
        ...createConfigMethods(mongoose),
    };
}

export { createMethods };
//# sourceMappingURL=index.es.js.map
