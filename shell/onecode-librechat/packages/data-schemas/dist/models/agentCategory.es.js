import agentCategorySchema from '../schema/agentCategory.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createAgentCategoryModel(mongoose) {
    applyTenantIsolation(agentCategorySchema);
    return (mongoose.models.AgentCategory ||
        mongoose.model('AgentCategory', agentCategorySchema));
}

export { createAgentCategoryModel };
//# sourceMappingURL=agentCategory.es.js.map
