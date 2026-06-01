import mcpServerSchema from '../schema/mcpServer.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createMCPServerModel(mongoose) {
    applyTenantIsolation(mcpServerSchema);
    return (mongoose.models.MCPServer || mongoose.model('MCPServer', mcpServerSchema));
}

export { createMCPServerModel };
//# sourceMappingURL=mcpServer.es.js.map
