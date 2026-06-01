import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';
import mongoMeili from './plugins/mongoMeili.es.js';
import messageSchema from '../schema/message.es.js';

function createMessageModel(mongoose) {
    applyTenantIsolation(messageSchema);
    if (process.env.MEILI_HOST && process.env.MEILI_MASTER_KEY) {
        messageSchema.plugin(mongoMeili, {
            mongoose,
            host: process.env.MEILI_HOST,
            apiKey: process.env.MEILI_MASTER_KEY,
            indexName: 'messages',
            primaryKey: 'messageId',
        });
    }
    return mongoose.models.Message || mongoose.model('Message', messageSchema);
}

export { createMessageModel };
//# sourceMappingURL=message.es.js.map
