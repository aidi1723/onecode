'use strict';

var user = require('../schema/user.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createUserModel(mongoose) {
    tenantIsolation.applyTenantIsolation(user);
    return mongoose.models.User || mongoose.model('User', user);
}

exports.createUserModel = createUserModel;
//# sourceMappingURL=user.cjs.map
