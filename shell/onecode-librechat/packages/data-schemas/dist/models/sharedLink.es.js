import shareSchema from '../schema/share.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createSharedLinkModel(mongoose) {
    applyTenantIsolation(shareSchema);
    return mongoose.models.SharedLink || mongoose.model('SharedLink', shareSchema);
}

export { createSharedLinkModel };
//# sourceMappingURL=sharedLink.es.js.map
