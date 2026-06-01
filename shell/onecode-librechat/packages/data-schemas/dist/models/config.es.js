import configSchema from '../schema/config.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createConfigModel(mongoose) {
    applyTenantIsolation(configSchema);
    return mongoose.models.Config || mongoose.model('Config', configSchema);
}

export { createConfigModel };
//# sourceMappingURL=config.es.js.map
