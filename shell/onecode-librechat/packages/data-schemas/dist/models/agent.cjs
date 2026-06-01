'use strict';

var agent = require('../schema/agent.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createAgentModel(mongoose) {
    tenantIsolation.applyTenantIsolation(agent);
    return mongoose.models.Agent || mongoose.model('Agent', agent);
}

exports.createAgentModel = createAgentModel;
//# sourceMappingURL=agent.cjs.map
