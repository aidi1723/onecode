import systemGrantSchema from '../schema/systemGrant.es.js';

/**
 * SystemGrant is a cross-tenant control plane — its query logic in systemGrant methods
 * explicitly handles tenantId conditions (platform-level vs tenant-scoped grants).
 * Do NOT apply tenant isolation plugin here; it would inject a hard tenantId equality
 * filter that conflicts with the $and/$or logic in hasCapabilityForPrincipals.
 */
function createSystemGrantModel(mongoose) {
    return (mongoose.models.SystemGrant || mongoose.model('SystemGrant', systemGrantSchema));
}

export { createSystemGrantModel };
//# sourceMappingURL=systemGrant.es.js.map
