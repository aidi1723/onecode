'use strict';

var memory = require('../schema/memory.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createMemoryModel(mongoose) {
    tenantIsolation.applyTenantIsolation(memory);
    return mongoose.models.MemoryEntry || mongoose.model('MemoryEntry', memory);
}

exports.createMemoryModel = createMemoryModel;
//# sourceMappingURL=memory.cjs.map
