'use strict';

var accessRole = require('../schema/accessRole.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createAccessRoleModel(mongoose) {
    tenantIsolation.applyTenantIsolation(accessRole);
    return (mongoose.models.AccessRole || mongoose.model('AccessRole', accessRole));
}

exports.createAccessRoleModel = createAccessRoleModel;
//# sourceMappingURL=accessRole.cjs.map
