'use strict';

var pluginAuth = require('../schema/pluginAuth.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createPluginAuthModel(mongoose) {
    tenantIsolation.applyTenantIsolation(pluginAuth);
    return mongoose.models.PluginAuth || mongoose.model('PluginAuth', pluginAuth);
}

exports.createPluginAuthModel = createPluginAuthModel;
//# sourceMappingURL=pluginAuth.cjs.map
