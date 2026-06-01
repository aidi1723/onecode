'use strict';

var assistant = require('../schema/assistant.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createAssistantModel(mongoose) {
    tenantIsolation.applyTenantIsolation(assistant);
    return mongoose.models.Assistant || mongoose.model('Assistant', assistant);
}

exports.createAssistantModel = createAssistantModel;
//# sourceMappingURL=assistant.cjs.map
