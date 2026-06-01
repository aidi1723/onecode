'use strict';

var mcpServer = require('../schema/mcpServer.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createMCPServerModel(mongoose) {
    tenantIsolation.applyTenantIsolation(mcpServer);
    return (mongoose.models.MCPServer || mongoose.model('MCPServer', mcpServer));
}

exports.createMCPServerModel = createMCPServerModel;
//# sourceMappingURL=mcpServer.cjs.map
