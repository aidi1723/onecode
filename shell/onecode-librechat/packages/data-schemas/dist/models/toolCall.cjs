'use strict';

var toolCall = require('../schema/toolCall.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createToolCallModel(mongoose) {
    tenantIsolation.applyTenantIsolation(toolCall);
    return mongoose.models.ToolCall || mongoose.model('ToolCall', toolCall);
}

exports.createToolCallModel = createToolCallModel;
//# sourceMappingURL=toolCall.cjs.map
