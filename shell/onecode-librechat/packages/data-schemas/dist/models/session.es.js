import sessionSchema from '../schema/session.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createSessionModel(mongoose) {
    applyTenantIsolation(sessionSchema);
    return mongoose.models.Session || mongoose.model('Session', sessionSchema);
}

export { createSessionModel };
//# sourceMappingURL=session.es.js.map
