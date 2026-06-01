'use strict';

var winston = require('../config/winston.cjs');

function createBannerMethods(mongoose) {
    /**
     * Retrieves the current active banner.
     */
    async function getBanner(user) {
        try {
            const Banner = mongoose.models.Banner;
            const now = new Date();
            const banner = (await Banner.findOne({
                displayFrom: { $lte: now },
                $or: [{ displayTo: { $gte: now } }, { displayTo: null }],
                type: 'banner',
            }).lean());
            if (!banner || banner.isPublic || user != null) {
                return banner;
            }
            return null;
        }
        catch (error) {
            winston.error('[getBanners] Error getting banners', error);
            throw new Error('Error getting banners');
        }
    }
    return { getBanner };
}

exports.createBannerMethods = createBannerMethods;
//# sourceMappingURL=banner.cjs.map
