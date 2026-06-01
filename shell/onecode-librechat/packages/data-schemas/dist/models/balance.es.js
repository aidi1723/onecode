import balanceSchema from '../schema/balance.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createBalanceModel(mongoose) {
    applyTenantIsolation(balanceSchema);
    return mongoose.models.Balance || mongoose.model('Balance', balanceSchema);
}

export { createBalanceModel };
//# sourceMappingURL=balance.es.js.map
