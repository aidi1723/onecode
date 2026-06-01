import pluginAuthSchema from '../schema/pluginAuth.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createPluginAuthModel(mongoose) {
    applyTenantIsolation(pluginAuthSchema);
    return mongoose.models.PluginAuth || mongoose.model('PluginAuth', pluginAuthSchema);
}

export { createPluginAuthModel };
//# sourceMappingURL=pluginAuth.es.js.map
