'use strict';

var action = require('../schema/action.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createActionModel(mongoose) {
    tenantIsolation.applyTenantIsolation(action);
    return mongoose.models.Action || mongoose.model('Action', action);
}

exports.createActionModel = createActionModel;
//# sourceMappingURL=action.cjs.map
