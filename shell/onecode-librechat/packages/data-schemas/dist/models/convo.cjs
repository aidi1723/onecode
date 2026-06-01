'use strict';

var tenantIsolation = require('./plugins/tenantIsolation.cjs');
var mongoMeili = require('./plugins/mongoMeili.cjs');
var convo = require('../schema/convo.cjs');

function createConversationModel(mongoose) {
    tenantIsolation.applyTenantIsolation(convo);
    if (process.env.MEILI_HOST && process.env.MEILI_MASTER_KEY) {
        convo.plugin(mongoMeili, {
            mongoose,
            host: process.env.MEILI_HOST,
            apiKey: process.env.MEILI_MASTER_KEY,
            /** Note: Will get created automatically if it doesn't exist already */
            indexName: 'convos',
            primaryKey: 'conversationId',
        });
    }
    return (mongoose.models.Conversation || mongoose.model('Conversation', convo));
}

exports.createConversationModel = createConversationModel;
//# sourceMappingURL=convo.cjs.map
