import { DEFAULT_RETENTION_HOURS } from './tempChatRetention.es.js';

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
const createFallbackRetentionDate = (now = Date.now()) => new Date(now + DEFAULT_RETENTION_HOURS * 60 * 60 * 1000);

export { activeExpirationFilter, buildRetentionVisibilityFilter, createFallbackRetentionDate, legacyPermanentExpirationFilter };
//# sourceMappingURL=retention.es.js.map
