'use strict';

var async_hooks = require('async_hooks');

/** Sentinel value for deliberate cross-tenant system operations */
const SYSTEM_TENANT_ID = '__SYSTEM__';
/**
 * AsyncLocalStorage instance for propagating tenant context.
 * Callbacks passed to `tenantStorage.run()` must be `async` for the context to propagate
 * through Mongoose query execution. Sync callbacks returning a Mongoose thenable will lose context.
 */
const tenantStorage = new async_hooks.AsyncLocalStorage();
/** Returns the current tenant ID from async context, or undefined if none is set */
function getTenantId() {
    var _a;
    return (_a = tenantStorage.getStore()) === null || _a === void 0 ? void 0 : _a.tenantId;
}
/** Returns the current user ID from async context, or undefined if none is set */
function getUserId() {
    var _a;
    return (_a = tenantStorage.getStore()) === null || _a === void 0 ? void 0 : _a.userId;
}
/** Returns the current request ID from async context, or undefined if none is set */
function getRequestId() {
    var _a;
    return (_a = tenantStorage.getStore()) === null || _a === void 0 ? void 0 : _a.requestId;
}
/**
 * Runs a function in an explicit cross-tenant system context (bypasses tenant filtering).
 * The callback MUST be async — sync callbacks returning Mongoose thenables will lose context.
 */
function runAsSystem(fn) {
    var _a;
    const { requestId, userId } = (_a = tenantStorage.getStore()) !== null && _a !== void 0 ? _a : {};
    return tenantStorage.run({ tenantId: SYSTEM_TENANT_ID, requestId, userId }, fn);
}
/**
 * Appends `:${tenantId}` to a cache key when a non-system tenant context is active.
 * Returns the base key unchanged when no ALS context is set or when running
 * inside `runAsSystem()` (SYSTEM_TENANT_ID context).
 */
function scopedCacheKey(baseKey) {
    const tenantId = getTenantId();
    if (!tenantId || tenantId === SYSTEM_TENANT_ID) {
        return baseKey;
    }
    return `${baseKey}:${tenantId}`;
}

exports.SYSTEM_TENANT_ID = SYSTEM_TENANT_ID;
exports.getRequestId = getRequestId;
exports.getTenantId = getTenantId;
exports.getUserId = getUserId;
exports.runAsSystem = runAsSystem;
exports.scopedCacheKey = scopedCacheKey;
exports.tenantStorage = tenantStorage;
//# sourceMappingURL=tenantContext.cjs.map
