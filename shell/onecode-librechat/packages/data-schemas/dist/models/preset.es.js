import presetSchema from '../schema/preset.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createPresetModel(mongoose) {
    applyTenantIsolation(presetSchema);
    return mongoose.models.Preset || mongoose.model('Preset', presetSchema);
}

export { createPresetModel };
//# sourceMappingURL=preset.es.js.map
