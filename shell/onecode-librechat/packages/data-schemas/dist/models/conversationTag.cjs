'use strict';

var conversationTag = require('../schema/conversationTag.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createConversationTagModel(mongoose) {
    tenantIsolation.applyTenantIsolation(conversationTag);
    return (mongoose.models.ConversationTag ||
        mongoose.model('ConversationTag', conversationTag));
}

exports.createConversationTagModel = createConversationTagModel;
//# sourceMappingURL=conversationTag.cjs.map
