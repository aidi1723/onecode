import transactionSchema from '../schema/transaction.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createTransactionModel(mongoose) {
    applyTenantIsolation(transactionSchema);
    return (mongoose.models.Transaction || mongoose.model('Transaction', transactionSchema));
}

export { createTransactionModel };
//# sourceMappingURL=transaction.es.js.map
