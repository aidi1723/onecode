import skillFileSchema from '../schema/skillFile.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createSkillFileModel(mongoose) {
    applyTenantIsolation(skillFileSchema);
    return (mongoose.models.SkillFile || mongoose.model('SkillFile', skillFileSchema));
}

export { createSkillFileModel };
//# sourceMappingURL=skillFile.es.js.map
