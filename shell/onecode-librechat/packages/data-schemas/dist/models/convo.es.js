import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';
import mongoMeili from './plugins/mongoMeili.es.js';
import convoSchema from '../schema/convo.es.js';

function createConversationModel(mongoose) {
    applyTenantIsolation(convoSchema);
    if (process.env.MEILI_HOST && process.env.MEILI_MASTER_KEY) {
        convoSchema.plugin(mongoMeili, {
            mongoose,
            host: process.env.MEILI_HOST,
            apiKey: process.env.MEILI_MASTER_KEY,
            /** Note: Will get created automatically if it doesn't exist already */
            indexName: 'convos',
            primaryKey: 'conversationId',
        });
    }
    return (mongoose.models.Conversation || mongoose.model('Conversation', convoSchema));
}

export { createConversationModel };
//# sourceMappingURL=convo.es.js.map
