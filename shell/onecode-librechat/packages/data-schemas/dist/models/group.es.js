import groupSchema from '../schema/group.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createGroupModel(mongoose) {
    applyTenantIsolation(groupSchema);
    return mongoose.models.Group || mongoose.model('Group', groupSchema);
}

export { createGroupModel };
//# sourceMappingURL=group.es.js.map
