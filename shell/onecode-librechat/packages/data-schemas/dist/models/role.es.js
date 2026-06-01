import roleSchema from '../schema/role.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createRoleModel(mongoose) {
    applyTenantIsolation(roleSchema);
    return mongoose.models.Role || mongoose.model('Role', roleSchema);
}

export { createRoleModel };
//# sourceMappingURL=role.es.js.map
