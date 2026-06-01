'use strict';

var user = require('./user.cjs');
var token = require('./token.cjs');
var session = require('./session.cjs');
var balance = require('./balance.cjs');
var convo = require('./convo.cjs');
var message = require('./message.cjs');
var agent = require('./agent.cjs');
var agentApiKey = require('./agentApiKey.cjs');
var agentCategory = require('./agentCategory.cjs');
var mcpServer = require('./mcpServer.cjs');
var role = require('./role.cjs');
var action = require('./action.cjs');
var assistant = require('./assistant.cjs');
var file = require('./file.cjs');
var banner = require('./banner.cjs');
var key = require('./key.cjs');
var pluginAuth = require('./pluginAuth.cjs');
var transaction = require('./transaction.cjs');
var preset = require('./preset.cjs');
var prompt = require('./prompt.cjs');
var promptGroup = require('./promptGroup.cjs');
var skill = require('./skill.cjs');
var skillFile = require('./skillFile.cjs');
var conversationTag = require('./conversationTag.cjs');
var sharedLink = require('./sharedLink.cjs');
var toolCall = require('./toolCall.cjs');
var memory = require('./memory.cjs');
var accessRole = require('./accessRole.cjs');
var aclEntry = require('./aclEntry.cjs');
var systemGrant = require('./systemGrant.cjs');
var group = require('./group.cjs');
var config = require('./config.cjs');

/**
 * Creates all database models for all collections
 */
function createModels(mongoose) {
    return {
        User: user.createUserModel(mongoose),
        Token: token.createTokenModel(mongoose),
        Session: session.createSessionModel(mongoose),
        Balance: balance.createBalanceModel(mongoose),
        Conversation: convo.createConversationModel(mongoose),
        Message: message.createMessageModel(mongoose),
        Agent: agent.createAgentModel(mongoose),
        AgentApiKey: agentApiKey.createAgentApiKeyModel(mongoose),
        AgentCategory: agentCategory.createAgentCategoryModel(mongoose),
        MCPServer: mcpServer.createMCPServerModel(mongoose),
        Role: role.createRoleModel(mongoose),
        Action: action.createActionModel(mongoose),
        Assistant: assistant.createAssistantModel(mongoose),
        File: file.createFileModel(mongoose),
        Banner: banner.createBannerModel(mongoose),
        Key: key.createKeyModel(mongoose),
        PluginAuth: pluginAuth.createPluginAuthModel(mongoose),
        Transaction: transaction.createTransactionModel(mongoose),
        Preset: preset.createPresetModel(mongoose),
        Prompt: prompt.createPromptModel(mongoose),
        PromptGroup: promptGroup.createPromptGroupModel(mongoose),
        Skill: skill.createSkillModel(mongoose),
        SkillFile: skillFile.createSkillFileModel(mongoose),
        ConversationTag: conversationTag.createConversationTagModel(mongoose),
        SharedLink: sharedLink.createSharedLinkModel(mongoose),
        ToolCall: toolCall.createToolCallModel(mongoose),
        MemoryEntry: memory.createMemoryModel(mongoose),
        AccessRole: accessRole.createAccessRoleModel(mongoose),
        AclEntry: aclEntry.createAclEntryModel(mongoose),
        SystemGrant: systemGrant.createSystemGrantModel(mongoose),
        Group: group.createGroupModel(mongoose),
        Config: config.createConfigModel(mongoose),
    };
}

exports.createModels = createModels;
//# sourceMappingURL=index.cjs.map
