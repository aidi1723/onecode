'use strict';

var tenantIsolation = require('./plugins/tenantIsolation.cjs');
var mongoMeili = require('./plugins/mongoMeili.cjs');
var message = require('../schema/message.cjs');

function createMessageModel(mongoose) {
    tenantIsolation.applyTenantIsolation(message);
    if (process.env.MEILI_HOST && process.env.MEILI_MASTER_KEY) {
        message.plugin(mongoMeili, {
            mongoose,
            host: process.env.MEILI_HOST,
            apiKey: process.env.MEILI_MASTER_KEY,
            indexName: 'messages',
            primaryKey: 'messageId',
        });
    }
    return mongoose.models.Message || mongoose.model('Message', message);
}

exports.createMessageModel = createMessageModel;
//# sourceMappingURL=message.cjs.map
