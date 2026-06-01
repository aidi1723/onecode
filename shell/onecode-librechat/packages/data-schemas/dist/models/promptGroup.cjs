'use strict';

var promptGroup = require('../schema/promptGroup.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createPromptGroupModel(mongoose) {
    tenantIsolation.applyTenantIsolation(promptGroup);
    return (mongoose.models.PromptGroup ||
        mongoose.model('PromptGroup', promptGroup));
}

exports.createPromptGroupModel = createPromptGroupModel;
//# sourceMappingURL=promptGroup.cjs.map
