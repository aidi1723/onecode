'use strict';

var share = require('../schema/share.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createSharedLinkModel(mongoose) {
    tenantIsolation.applyTenantIsolation(share);
    return mongoose.models.SharedLink || mongoose.model('SharedLink', share);
}

exports.createSharedLinkModel = createSharedLinkModel;
//# sourceMappingURL=sharedLink.cjs.map
