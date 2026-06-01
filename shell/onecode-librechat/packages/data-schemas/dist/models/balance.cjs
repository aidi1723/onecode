'use strict';

var balance = require('../schema/balance.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createBalanceModel(mongoose) {
    tenantIsolation.applyTenantIsolation(balance);
    return mongoose.models.Balance || mongoose.model('Balance', balance);
}

exports.createBalanceModel = createBalanceModel;
//# sourceMappingURL=balance.cjs.map
