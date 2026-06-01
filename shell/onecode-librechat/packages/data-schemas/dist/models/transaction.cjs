'use strict';

var transaction = require('../schema/transaction.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createTransactionModel(mongoose) {
    tenantIsolation.applyTenantIsolation(transaction);
    return (mongoose.models.Transaction || mongoose.model('Transaction', transaction));
}

exports.createTransactionModel = createTransactionModel;
//# sourceMappingURL=transaction.cjs.map
