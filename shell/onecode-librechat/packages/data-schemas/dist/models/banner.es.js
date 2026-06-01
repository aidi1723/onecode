import bannerSchema from '../schema/banner.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createBannerModel(mongoose) {
    applyTenantIsolation(bannerSchema);
    return mongoose.models.Banner || mongoose.model('Banner', bannerSchema);
}

export { createBannerModel };
//# sourceMappingURL=banner.es.js.map
