import promptSchema from '../schema/prompt.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createPromptModel(mongoose) {
    applyTenantIsolation(promptSchema);
    return mongoose.models.Prompt || mongoose.model('Prompt', promptSchema);
}

export { createPromptModel };
//# sourceMappingURL=prompt.es.js.map
