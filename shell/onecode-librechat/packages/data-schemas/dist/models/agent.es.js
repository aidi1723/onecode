import agentSchema from '../schema/agent.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createAgentModel(mongoose) {
    applyTenantIsolation(agentSchema);
    return mongoose.models.Agent || mongoose.model('Agent', agentSchema);
}

export { createAgentModel };
//# sourceMappingURL=agent.es.js.map
