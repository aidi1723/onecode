'use strict';

var config = require('../schema/config.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createConfigModel(mongoose) {
    tenantIsolation.applyTenantIsolation(config);
    return mongoose.models.Config || mongoose.model('Config', config);
}

exports.createConfigModel = createConfigModel;
//# sourceMappingURL=config.cjs.map
