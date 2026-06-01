'use strict';

var group = require('../schema/group.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createGroupModel(mongoose) {
    tenantIsolation.applyTenantIsolation(group);
    return mongoose.models.Group || mongoose.model('Group', group);
}

exports.createGroupModel = createGroupModel;
//# sourceMappingURL=group.cjs.map
