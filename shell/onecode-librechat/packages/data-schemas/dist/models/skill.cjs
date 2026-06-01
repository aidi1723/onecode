'use strict';

var skill = require('../schema/skill.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createSkillModel(mongoose) {
    tenantIsolation.applyTenantIsolation(skill);
    return mongoose.models.Skill || mongoose.model('Skill', skill);
}

exports.createSkillModel = createSkillModel;
//# sourceMappingURL=skill.cjs.map
