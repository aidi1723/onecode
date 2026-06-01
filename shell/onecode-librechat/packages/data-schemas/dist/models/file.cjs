'use strict';

var file = require('../schema/file.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createFileModel(mongoose) {
    tenantIsolation.applyTenantIsolation(file);
    return mongoose.models.File || mongoose.model('File', file);
}

exports.createFileModel = createFileModel;
//# sourceMappingURL=file.cjs.map
