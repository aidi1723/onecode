'use strict';

var session = require('../schema/session.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createSessionModel(mongoose) {
    tenantIsolation.applyTenantIsolation(session);
    return mongoose.models.Session || mongoose.model('Session', session);
}

exports.createSessionModel = createSessionModel;
//# sourceMappingURL=session.cjs.map
