'use strict';

var prompt = require('../schema/prompt.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createPromptModel(mongoose) {
    tenantIsolation.applyTenantIsolation(prompt);
    return mongoose.models.Prompt || mongoose.model('Prompt', prompt);
}

exports.createPromptModel = createPromptModel;
//# sourceMappingURL=prompt.cjs.map
