'use strict';

var agentCategory = require('../schema/agentCategory.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createAgentCategoryModel(mongoose) {
    tenantIsolation.applyTenantIsolation(agentCategory);
    return (mongoose.models.AgentCategory ||
        mongoose.model('AgentCategory', agentCategory));
}

exports.createAgentCategoryModel = createAgentCategoryModel;
//# sourceMappingURL=agentCategory.cjs.map
