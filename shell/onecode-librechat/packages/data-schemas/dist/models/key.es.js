import keySchema from '../schema/key.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createKeyModel(mongoose) {
    applyTenantIsolation(keySchema);
    return mongoose.models.Key || mongoose.model('Key', keySchema);
}

export { createKeyModel };
//# sourceMappingURL=key.es.js.map
