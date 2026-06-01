import tokenSchema from '../schema/token.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createTokenModel(mongoose) {
    applyTenantIsolation(tokenSchema);
    return mongoose.models.Token || mongoose.model('Token', tokenSchema);
}

export { createTokenModel };
//# sourceMappingURL=token.es.js.map
