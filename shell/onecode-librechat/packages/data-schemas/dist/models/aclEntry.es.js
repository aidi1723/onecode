import aclEntrySchema from '../schema/aclEntry.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createAclEntryModel(mongoose) {
    applyTenantIsolation(aclEntrySchema);
    return mongoose.models.AclEntry || mongoose.model('AclEntry', aclEntrySchema);
}

export { createAclEntryModel };
//# sourceMappingURL=aclEntry.es.js.map
