'use strict';

var preset = require('../schema/preset.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createPresetModel(mongoose) {
    tenantIsolation.applyTenantIsolation(preset);
    return mongoose.models.Preset || mongoose.model('Preset', preset);
}

exports.createPresetModel = createPresetModel;
//# sourceMappingURL=preset.cjs.map
