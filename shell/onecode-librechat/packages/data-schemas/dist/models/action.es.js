import Action from '../schema/action.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createActionModel(mongoose) {
    applyTenantIsolation(Action);
    return mongoose.models.Action || mongoose.model('Action', Action);
}

export { createActionModel };
//# sourceMappingURL=action.es.js.map
