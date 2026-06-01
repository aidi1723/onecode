import { createUserModel } from './user.es.js';
import { createTokenModel } from './token.es.js';
import { createSessionModel } from './session.es.js';
import { createBalanceModel } from './balance.es.js';
import { createConversationModel } from './convo.es.js';
import { createMessageModel } from './message.es.js';
import { createAgentModel } from './agent.es.js';
import { createAgentApiKeyModel } from './agentApiKey.es.js';
import { createAgentCategoryModel } from './agentCategory.es.js';
import { createMCPServerModel } from './mcpServer.es.js';
import { createRoleModel } from './role.es.js';
import { createActionModel } from './action.es.js';
import { createAssistantModel } from './assistant.es.js';
import { createFileModel } from './file.es.js';
import { createBannerModel } from './banner.es.js';
import { createKeyModel } from './key.es.js';
import { createPluginAuthModel } from './pluginAuth.es.js';
import { createTransactionModel } from './transaction.es.js';
import { createPresetModel } from './preset.es.js';
import { createPromptModel } from './prompt.es.js';
import { createPromptGroupModel } from './promptGroup.es.js';
import { createSkillModel } from './skill.es.js';
import { createSkillFileModel } from './skillFile.es.js';
import { createConversationTagModel } from './conversationTag.es.js';
import { createSharedLinkModel } from './sharedLink.es.js';
import { createToolCallModel } from './toolCall.es.js';
import { createMemoryModel } from './memory.es.js';
import { createAccessRoleModel } from './accessRole.es.js';
import { createAclEntryModel } from './aclEntry.es.js';
import { createSystemGrantModel } from './systemGrant.es.js';
import { createGroupModel } from './group.es.js';
import { createConfigModel } from './config.es.js';

/**
 * Creates all database models for all collections
 */
function createModels(mongoose) {
    return {
        User: createUserModel(mongoose),
        Token: createTokenModel(mongoose),
        Session: createSessionModel(mongoose),
        Balance: createBalanceModel(mongoose),
        Conversation: createConversationModel(mongoose),
        Message: createMessageModel(mongoose),
        Agent: createAgentModel(mongoose),
        AgentApiKey: createAgentApiKeyModel(mongoose),
        AgentCategory: createAgentCategoryModel(mongoose),
        MCPServer: createMCPServerModel(mongoose),
        Role: createRoleModel(mongoose),
        Action: createActionModel(mongoose),
        Assistant: createAssistantModel(mongoose),
        File: createFileModel(mongoose),
        Banner: createBannerModel(mongoose),
        Key: createKeyModel(mongoose),
        PluginAuth: createPluginAuthModel(mongoose),
        Transaction: createTransactionModel(mongoose),
        Preset: createPresetModel(mongoose),
        Prompt: createPromptModel(mongoose),
        PromptGroup: createPromptGroupModel(mongoose),
        Skill: createSkillModel(mongoose),
        SkillFile: createSkillFileModel(mongoose),
        ConversationTag: createConversationTagModel(mongoose),
        SharedLink: createSharedLinkModel(mongoose),
        ToolCall: createToolCallModel(mongoose),
        MemoryEntry: createMemoryModel(mongoose),
        AccessRole: createAccessRoleModel(mongoose),
        AclEntry: createAclEntryModel(mongoose),
        SystemGrant: createSystemGrantModel(mongoose),
        Group: createGroupModel(mongoose),
        Config: createConfigModel(mongoose),
    };
}

export { createModels };
//# sourceMappingURL=index.es.js.map
