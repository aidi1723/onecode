'use strict';

var banner = require('../schema/banner.cjs');
var tenantIsolation = require('./plugins/tenantIsolation.cjs');

function createBannerModel(mongoose) {
    tenantIsolation.applyTenantIsolation(banner);
    return mongoose.models.Banner || mongoose.model('Banner', banner);
}

exports.createBannerModel = createBannerModel;
//# sourceMappingURL=banner.cjs.map
