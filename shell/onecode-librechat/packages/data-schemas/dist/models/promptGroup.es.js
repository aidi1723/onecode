import promptGroupSchema from '../schema/promptGroup.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createPromptGroupModel(mongoose) {
    applyTenantIsolation(promptGroupSchema);
    return (mongoose.models.PromptGroup ||
        mongoose.model('PromptGroup', promptGroupSchema));
}

export { createPromptGroupModel };
//# sourceMappingURL=promptGroup.es.js.map
