import skillSchema from '../schema/skill.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createSkillModel(mongoose) {
    applyTenantIsolation(skillSchema);
    return mongoose.models.Skill || mongoose.model('Skill', skillSchema);
}

export { createSkillModel };
//# sourceMappingURL=skill.es.js.map
