'use strict';

var tempChatRetention = require('./tempChatRetention.cjs');

const activeExpirationFilter = () => ({
    $or: [{ expiredAt: null }, { expiredAt: { $gt: new Date() } }],
});
const legacyPermanentExpirationFilter = () => ({ expiredAt: null });
const buildRetentionVisibilityFilter = () => ({
    $or: [
        { isTemporary: false, expiredAt: null },
        { isTemporary: false, expiredAt: { $gt: new Date() } },
        { isTemporary: null, expiredAt: null },
    ],
});
const createFallbackRetentionDate = (now = Date.now()) => new Date(now + tempChatRetention.DEFAULT_RETENTION_HOURS * 60 * 60 * 1000);

exports.activeExpirationFilter = activeExpirationFilter;
exports.buildRetentionVisibilityFilter = buildRetentionVisibilityFilter;
exports.createFallbackRetentionDate = createFallbackRetentionDate;
exports.legacyPermanentExpirationFilter = legacyPermanentExpirationFilter;
//# sourceMappingURL=retention.cjs.map
