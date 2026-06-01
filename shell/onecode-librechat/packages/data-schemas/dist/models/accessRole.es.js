import accessRoleSchema from '../schema/accessRole.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createAccessRoleModel(mongoose) {
    applyTenantIsolation(accessRoleSchema);
    return (mongoose.models.AccessRole || mongoose.model('AccessRole', accessRoleSchema));
}

export { createAccessRoleModel };
//# sourceMappingURL=accessRole.es.js.map
