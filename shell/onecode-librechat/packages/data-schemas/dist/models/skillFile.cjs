'use strict';

var skillFile = require('../schema/skillFile.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createSkillFileModel(mongoose) {
    tenantIsolation.applyTenantIsolation(skillFile);
    return (mongoose.models.SkillFile || mongoose.model('SkillFile', skillFile));
}

exports.createSkillFileModel = createSkillFileModel;
//# sourceMappingURL=skillFile.cjs.map
