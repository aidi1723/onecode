import agentApiKeySchema from '../schema/agentApiKey.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createAgentApiKeyModel(mongoose) {
    applyTenantIsolation(agentApiKeySchema);
    return (mongoose.models.AgentApiKey || mongoose.model('AgentApiKey', agentApiKeySchema));
}

export { createAgentApiKeyModel };
//# sourceMappingURL=agentApiKey.es.js.map
