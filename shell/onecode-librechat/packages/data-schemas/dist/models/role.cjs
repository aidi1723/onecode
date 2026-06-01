'use strict';

var role = require('../schema/role.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createRoleModel(mongoose) {
    tenantIsolation.applyTenantIsolation(role);
    return mongoose.models.Role || mongoose.model('Role', role);
}

exports.createRoleModel = createRoleModel;
//# sourceMappingURL=role.cjs.map
