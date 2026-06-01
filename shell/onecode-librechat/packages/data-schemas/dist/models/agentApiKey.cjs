'use strict';

var agentApiKey = require('../schema/agentApiKey.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createAgentApiKeyModel(mongoose) {
    tenantIsolation.applyTenantIsolation(agentApiKey);
    return (mongoose.models.AgentApiKey || mongoose.model('AgentApiKey', agentApiKey));
}

exports.createAgentApiKeyModel = createAgentApiKeyModel;
//# sourceMappingURL=agentApiKey.cjs.map
