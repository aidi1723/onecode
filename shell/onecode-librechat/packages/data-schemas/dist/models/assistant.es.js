import assistantSchema from '../schema/assistant.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createAssistantModel(mongoose) {
    applyTenantIsolation(assistantSchema);
    return mongoose.models.Assistant || mongoose.model('Assistant', assistantSchema);
}

export { createAssistantModel };
//# sourceMappingURL=assistant.es.js.map
