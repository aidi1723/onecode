'use strict';

var aclEntry = require('../schema/aclEntry.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createAclEntryModel(mongoose) {
    tenantIsolation.applyTenantIsolation(aclEntry);
    return mongoose.models.AclEntry || mongoose.model('AclEntry', aclEntry);
}

exports.createAclEntryModel = createAclEntryModel;
//# sourceMappingURL=aclEntry.cjs.map
