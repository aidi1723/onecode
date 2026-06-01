'use strict';

var token = require('../schema/token.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createTokenModel(mongoose) {
    tenantIsolation.applyTenantIsolation(token);
    return mongoose.models.Token || mongoose.model('Token', token);
}

exports.createTokenModel = createTokenModel;
//# sourceMappingURL=token.cjs.map
