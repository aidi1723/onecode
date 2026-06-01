import logger from '../config/winston.es.js';

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
            logger.error('[getBanners] Error getting banners', error);
            throw new Error('Error getting banners');
        }
    }
    return { getBanner };
}

export { createBannerMethods };
//# sourceMappingURL=banner.es.js.map
