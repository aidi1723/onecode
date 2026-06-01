import toolCallSchema from '../schema/toolCall.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createToolCallModel(mongoose) {
    applyTenantIsolation(toolCallSchema);
    return mongoose.models.ToolCall || mongoose.model('ToolCall', toolCallSchema);
}

export { createToolCallModel };
//# sourceMappingURL=toolCall.es.js.map
