import conversationTag from '../schema/conversationTag.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createConversationTagModel(mongoose) {
    applyTenantIsolation(conversationTag);
    return (mongoose.models.ConversationTag ||
        mongoose.model('ConversationTag', conversationTag));
}

export { createConversationTagModel };
//# sourceMappingURL=conversationTag.es.js.map
