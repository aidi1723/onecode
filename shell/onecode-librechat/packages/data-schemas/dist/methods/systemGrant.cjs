'use strict';

var librechatDataProvider = require('librechat-data-provider');
var capabilities = require('../admin/capabilities.cjs');
var tenantBulkWrite = require('../utils/tenantBulkWrite.cjs');
var principal = require('../utils/principal.cjs');
var winston = require('../config/winston.cjs');

var _a;
const reverseImplications = {};
for (const [broad, implied] of Object.entries(capabilities.CapabilityImplications)) {
    for (const cap of implied) {
        ((_a = reverseImplications[cap]) !== null && _a !== void 0 ? _a : (reverseImplications[cap] = [])).push(broad);
    }
}
const baseCapabilityValues = new Set(Object.values(capabilities.SystemCapabilities));
/**
 * For a section/assignment capability like `manage:configs:endpoints` or
 * `assign:configs:user`, returns all base capabilities that subsume it:
 * the direct parent (`manage:configs`) plus any that imply the parent
 * via `reverseImplications` (`manage:configs` has no reverse, but
 * `read:configs` is implied by `manage:configs`—so `read:configs:endpoints`
 * is satisfied by holding `manage:configs`).
 */
function getParentCapabilities(capability) {
    const lastColon = capability.lastIndexOf(':');
    if (lastColon === -1) {
        return [];
    }
    const parent = capability.slice(0, lastColon);
    if (!baseCapabilityValues.has(parent)) {
        return [];
    }
    const parents = [parent];
    const implied = reverseImplications[parent];
    if (implied) {
        parents.push(...implied);
    }
    return parents;
}
function createSystemGrantMethods(mongoose) {
    function tenantCondition(tenantId) {
        return tenantId != null
            ? { $and: [{ $or: [{ tenantId }, { tenantId: { $exists: false } }] }] }
            : { tenantId: { $exists: false } };
    }
    /**
     * Check if any of the given principals holds a specific capability.
     * Follows the same principal-resolution pattern as AclEntry:
     * getUserPrincipals → $or query.
     *
     * @param principals - Resolved principal list from getUserPrincipals
     * @param capability - The capability to check
     * @param tenantId  - If present, checks tenant-scoped grant; if absent, checks platform-level
     */
    async function hasCapabilityForPrincipals({ principals, capability, tenantId, }) {
        var _a;
        const SystemGrant = mongoose.models.SystemGrant;
        const principalsQuery = principals
            .filter((p) => p.principalType !== librechatDataProvider.PrincipalType.PUBLIC && p.principalId != null)
            .map((p) => ({
            principalType: p.principalType,
            principalId: principal.normalizePrincipalId(p.principalId, p.principalType),
        }));
        if (!principalsQuery.length) {
            return false;
        }
        const impliedBy = (_a = reverseImplications[capability]) !== null && _a !== void 0 ? _a : [];
        const parents = getParentCapabilities(capability);
        const allMatches = [capability, ...impliedBy, ...parents];
        const capabilityQuery = allMatches.length > 1 ? { $in: allMatches } : capability;
        const query = {
            $or: principalsQuery,
            capability: capabilityQuery,
            ...tenantCondition(tenantId),
        };
        const doc = await SystemGrant.exists(query);
        return doc != null;
    }
    /**
     * Returns the subset of `capabilities` that any of the given principals hold.
     * Single DB round-trip — replaces N parallel `hasCapabilityForPrincipals` calls.
     */
    async function getHeldCapabilities({ principals, capabilities, tenantId, }) {
        const SystemGrant = mongoose.models.SystemGrant;
        const principalsQuery = principals
            .filter((p) => p.principalType !== librechatDataProvider.PrincipalType.PUBLIC && p.principalId != null)
            .map((p) => ({
            principalType: p.principalType,
            principalId: principal.normalizePrincipalId(p.principalId, p.principalType),
        }));
        if (!principalsQuery.length || !capabilities.length) {
            return new Set();
        }
        const allCaps = new Set([
            ...capabilities,
            ...capabilities.flatMap((cap) => { var _a; return (_a = reverseImplications[cap]) !== null && _a !== void 0 ? _a : []; }),
            ...capabilities.flatMap(getParentCapabilities),
        ]);
        const docs = await SystemGrant.find({
            $or: principalsQuery,
            capability: { $in: [...allCaps] },
            ...tenantCondition(tenantId),
        }, { capability: 1, _id: 0 }).lean();
        const held = new Set(docs.map((d) => d.capability));
        const result = new Set();
        for (const cap of capabilities) {
            if (held.has(cap)) {
                result.add(cap);
                continue;
            }
            const implied = reverseImplications[cap];
            if (implied === null || implied === void 0 ? void 0 : implied.some((imp) => held.has(imp))) {
                result.add(cap);
                continue;
            }
            if (getParentCapabilities(cap).some((p) => held.has(p))) {
                result.add(cap);
            }
        }
        return result;
    }
    /**
     * Grant a capability to a principal. Upsert — idempotent.
     */
    async function grantCapability({ principalType, principalId, capability, tenantId, grantedBy, }, session) {
        const SystemGrant = mongoose.models.SystemGrant;
        const normalizedPrincipalId = principal.normalizePrincipalId(principalId, principalType);
        const filter = {
            principalType,
            principalId: normalizedPrincipalId,
            capability,
            tenantId: tenantId != null ? tenantId : { $exists: false },
        };
        const update = {
            $set: {
                grantedAt: new Date(),
                ...(grantedBy != null && { grantedBy }),
            },
            $setOnInsert: {
                principalType,
                principalId: normalizedPrincipalId,
                capability,
                ...(tenantId != null && { tenantId }),
            },
        };
        const options = {
            upsert: true,
            new: true,
            ...(session ? { session } : {}),
        };
        try {
            return await SystemGrant.findOneAndUpdate(filter, update, options);
        }
        catch (err) {
            if (err.code === 11000) {
                return (await SystemGrant.findOne(filter).lean());
            }
            throw err;
        }
    }
    /**
     * Revoke a capability from a principal.
     */
    async function revokeCapability({ principalType, principalId, capability, tenantId, }, session) {
        const SystemGrant = mongoose.models.SystemGrant;
        const normalizedPrincipalId = principal.normalizePrincipalId(principalId, principalType);
        const filter = {
            principalType,
            principalId: normalizedPrincipalId,
            capability,
            tenantId: tenantId != null ? tenantId : { $exists: false },
        };
        const options = session ? { session } : {};
        await SystemGrant.deleteOne(filter, options);
    }
    /**
     * List all capabilities held by a principal — used by the capabilities
     * introspection endpoint.
     */
    async function getCapabilitiesForPrincipal({ principalType, principalId, tenantId, }) {
        const SystemGrant = mongoose.models.SystemGrant;
        const filter = {
            principalType,
            principalId: principal.normalizePrincipalId(principalId, principalType),
            ...tenantCondition(tenantId),
        };
        return await SystemGrant.find(filter).lean();
    }
    const GRANTS_DEFAULT_LIMIT = 50;
    const GRANTS_MAX_LIMIT = 200;
    async function listGrants(options) {
        var _a, _b, _c;
        const SystemGrant = mongoose.models.SystemGrant;
        const limit = Math.min(GRANTS_MAX_LIMIT, Math.max(1, (_a = options === null || options === void 0 ? void 0 : options.limit) !== null && _a !== void 0 ? _a : GRANTS_DEFAULT_LIMIT));
        const offset = (_b = options === null || options === void 0 ? void 0 : options.offset) !== null && _b !== void 0 ? _b : 0;
        const filter = {
            ...(((_c = options === null || options === void 0 ? void 0 : options.principalTypes) === null || _c === void 0 ? void 0 : _c.length) && { principalType: { $in: options.principalTypes } }),
            ...tenantCondition(options === null || options === void 0 ? void 0 : options.tenantId),
        };
        return SystemGrant.find(filter)
            .sort({ principalType: 1, capability: 1 })
            .skip(offset)
            .limit(limit)
            .lean();
    }
    async function countGrants(options) {
        var _a;
        const SystemGrant = mongoose.models.SystemGrant;
        const filter = {
            ...(((_a = options === null || options === void 0 ? void 0 : options.principalTypes) === null || _a === void 0 ? void 0 : _a.length) && { principalType: { $in: options.principalTypes } }),
            ...tenantCondition(options === null || options === void 0 ? void 0 : options.tenantId),
        };
        return SystemGrant.countDocuments(filter);
    }
    async function getCapabilitiesForPrincipals({ principals, tenantId, }) {
        if (!principals.length) {
            return [];
        }
        const SystemGrant = mongoose.models.SystemGrant;
        const principalsQuery = principals
            .filter((p) => p.principalType !== librechatDataProvider.PrincipalType.PUBLIC)
            .map((p) => ({
            principalType: p.principalType,
            principalId: principal.normalizePrincipalId(p.principalId, p.principalType),
        }));
        if (!principalsQuery.length) {
            return [];
        }
        const filter = {
            $or: principalsQuery,
            ...tenantCondition(tenantId),
        };
        return await SystemGrant.find(filter).lean();
    }
    /**
     * Seed the ADMIN role with all system capabilities.
     * Context-agnostic: caller provides tenant context (e.g., `runAsSystem()` for
     * startup, `tenantStorage.run()` for future per-tenant provisioning).
     * Idempotent and concurrency-safe: uses bulkWrite with ordered:false so parallel
     * server instances (K8s rolling deploy, PM2 cluster) do not race on E11000.
     * Retries up to 3 times with exponential backoff on transient failures.
     */
    async function seedSystemGrants() {
        var _a;
        const maxRetries = 3;
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const SystemGrant = mongoose.models.SystemGrant;
                const now = new Date();
                const ops = Object.values(capabilities.SystemCapabilities).map((capability) => ({
                    updateOne: {
                        filter: {
                            principalType: librechatDataProvider.PrincipalType.ROLE,
                            principalId: librechatDataProvider.SystemRoles.ADMIN,
                            capability,
                            tenantId: { $exists: false },
                        },
                        update: {
                            $setOnInsert: {
                                principalType: librechatDataProvider.PrincipalType.ROLE,
                                principalId: librechatDataProvider.SystemRoles.ADMIN,
                                capability,
                                grantedAt: now,
                            },
                        },
                        upsert: true,
                    },
                }));
                await tenantBulkWrite.tenantSafeBulkWrite(SystemGrant, ops, { ordered: false });
                return;
            }
            catch (err) {
                if (attempt < maxRetries) {
                    const delay = 1000 * Math.pow(2, attempt - 1);
                    winston.warn(`[seedSystemGrants] Attempt ${attempt}/${maxRetries} failed, retrying in ${delay}ms: ${(_a = err.message) !== null && _a !== void 0 ? _a : String(err)}`);
                    await new Promise((resolve) => setTimeout(resolve, delay));
                }
                else {
                    winston.error('[seedSystemGrants] Failed to seed capabilities after all retries. ' +
                        'Admin panel access requires these grants. Manual recovery: ' +
                        'db.systemgrants.insertMany([...]) with ADMIN role grants for each capability.', err);
                }
            }
        }
    }
    /**
     * Delete system grants for a principal.
     * Used for cascade cleanup when a principal (group, role) is deleted.
     *
     * When `tenantId` is provided, only grants scoped to **exactly** that
     * tenant are removed — platform-level grants (no tenantId) are left
     * intact so they continue to serve other tenants.
     * When `tenantId` is omitted, ALL grants for the principal are removed
     * regardless of tenant scope.
     */
    async function deleteGrantsForPrincipal(principalType, principalId, options) {
        const SystemGrant = mongoose.models.SystemGrant;
        const normalizedPrincipalId = principal.normalizePrincipalId(principalId, principalType);
        const filter = {
            principalType,
            principalId: normalizedPrincipalId,
            ...((options === null || options === void 0 ? void 0 : options.tenantId) != null && { tenantId: options.tenantId }),
        };
        const queryOptions = (options === null || options === void 0 ? void 0 : options.session) ? { session: options.session } : {};
        await SystemGrant.deleteMany(filter, queryOptions);
    }
    return {
        grantCapability,
        seedSystemGrants,
        revokeCapability,
        hasCapabilityForPrincipals,
        getHeldCapabilities,
        listGrants,
        countGrants,
        getCapabilitiesForPrincipal,
        getCapabilitiesForPrincipals,
        deleteGrantsForPrincipal,
    };
}

exports.createSystemGrantMethods = createSystemGrantMethods;
//# sourceMappingURL=systemGrant.cjs.map
