'use strict';

var key = require('../schema/key.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createKeyModel(mongoose) {
    tenantIsolation.applyTenantIsolation(key);
    return mongoose.models.Key || mongoose.model('Key', key);
}

exports.createKeyModel = createKeyModel;
//# sourceMappingURL=key.cjs.map
