'use strict';

var shutdown = require('./shutdown-D22txQVt.js');
var http = require('node:http');
var sdkNode = require('@opentelemetry/sdk-node');
var resources = require('@opentelemetry/resources');
var instrumentationHttp = require('@opentelemetry/instrumentation-http');
var instrumentationUndici = require('@opentelemetry/instrumentation-undici');
var instrumentationIoredis = require('@opentelemetry/instrumentation-ioredis');
var instrumentationExpress = require('@opentelemetry/instrumentation-express');
var instrumentationMongodb = require('@opentelemetry/instrumentation-mongodb');
var instrumentationMongoose = require('@opentelemetry/instrumentation-mongoose');
var semanticConventions = require('@opentelemetry/semantic-conventions');
var api = require('@opentelemetry/api');
var node_perf_hooks = require('node:perf_hooks');
require('@librechat/data-schemas');

const DEFAULT_SERVICE_NAME = 'librechat';
const DEFAULT_HEALTH_PATH = '/health';
function isTruthy(value) {
    if (typeof value === 'boolean') {
        return value;
    }
    if (typeof value === 'string') {
        return value.trim().toLowerCase() === 'true';
    }
    return false;
}
function normalizeEnvValue(value) {
    const trimmed = value === null || value === void 0 ? void 0 : value.trim();
    return trimmed ? trimmed : undefined;
}
function getTelemetryConfig(env = process.env) {
    var _a, _b;
    const sdkDisabled = isTruthy(env.OTEL_SDK_DISABLED);
    const enabled = isTruthy(env.OTEL_TRACING_ENABLED) && !sdkDisabled;
    const serviceName = (_a = normalizeEnvValue(env.OTEL_SERVICE_NAME)) !== null && _a !== void 0 ? _a : DEFAULT_SERVICE_NAME;
    const serviceVersion = (_b = normalizeEnvValue(env.OTEL_SERVICE_VERSION)) !== null && _b !== void 0 ? _b : normalizeEnvValue(env.npm_package_version);
    return {
        enabled,
        serviceName,
        sdkDisabled,
        serviceVersion,
        healthPath: DEFAULT_HEALTH_PATH,
    };
}

const WARNING_CODE = 'LIBRECHAT_OTEL';
const REDACTED_QUERY_VALUE = '[REDACTED]';
const SIGNAL_SHUTDOWN_TIMEOUT_MS = 5000;
let activeSdk;
let pendingSdk;
let startPromise;
let shutdownPromise;
let status = 'stopped';
let shutdownTaskRegistered = false;
let requestSpans = new WeakMap();
function isBunRuntime() {
    return Reflect.get(globalThis, 'Bun') != null;
}
function shouldIgnoreIncomingRequest(request, healthPath) {
    var _a;
    return request.url === healthPath || ((_a = request.url) === null || _a === void 0 ? void 0 : _a.startsWith(`${healthPath}?`)) === true;
}
function getIncomingUrlInfo(request) {
    var _a;
    const rawUrl = (_a = request.url) !== null && _a !== void 0 ? _a : '/';
    try {
        const parsedUrl = new URL(rawUrl, 'http://localhost');
        return {
            hasQuery: parsedUrl.search.length > 1,
            pathname: parsedUrl.pathname || '/',
        };
    }
    catch (_b) {
        const queryIndex = rawUrl.indexOf('?');
        return {
            hasQuery: queryIndex >= 0 && queryIndex < rawUrl.length - 1,
            pathname: queryIndex >= 0 ? rawUrl.slice(0, queryIndex) || '/' : rawUrl || '/',
        };
    }
}
function getLowCardinalityUrlPath(pathname, healthPath) {
    if (pathname === healthPath) {
        return healthPath;
    }
    if (pathname === '/api' || pathname.startsWith('/api/')) {
        return '/api/*';
    }
    return 'spa_fallback';
}
function getSanitizedIncomingUrlAttributes(request, healthPath) {
    const { hasQuery, pathname } = getIncomingUrlInfo(request);
    const safePath = getLowCardinalityUrlPath(pathname, healthPath);
    const safeTarget = hasQuery ? `${safePath}?${REDACTED_QUERY_VALUE}` : safePath;
    const attributes = {
        'http.target': safeTarget,
        'http.url': safeTarget,
        'url.full': safeTarget,
        'url.path': safePath,
    };
    if (hasQuery) {
        attributes['url.query'] = REDACTED_QUERY_VALUE;
    }
    return attributes;
}
function getStringValue(value) {
    if (value == null) {
        return undefined;
    }
    const stringValue = String(value).trim();
    return stringValue || undefined;
}
function getRedactedQuery(search) {
    const query = search.startsWith('?') ? search.slice(1) : search;
    if (!query) {
        return undefined;
    }
    return query
        .split('&')
        .map((part) => {
        const separatorIndex = part.indexOf('=');
        if (separatorIndex < 0) {
            return REDACTED_QUERY_VALUE;
        }
        const key = part.slice(0, separatorIndex);
        if (!key) {
            return REDACTED_QUERY_VALUE;
        }
        return `${key}=${REDACTED_QUERY_VALUE}`;
    })
        .join('&');
}
function getSanitizedUrlAttributesFromParts(origin, pathname, search) {
    const path = pathname || '/';
    const redactedQuery = getRedactedQuery(search);
    const target = redactedQuery ? `${path}?${redactedQuery}` : path;
    const fullUrl = origin ? `${origin}${target}` : target;
    const attributes = {
        'http.target': target,
        'http.url': fullUrl,
        'url.full': fullUrl,
        'url.path': path,
    };
    if (redactedQuery) {
        attributes['url.query'] = redactedQuery;
    }
    return attributes;
}
function getFallbackUrlParts(rawUrl) {
    const queryIndex = rawUrl.indexOf('?');
    if (queryIndex < 0) {
        return { pathname: rawUrl || '/', search: '' };
    }
    return {
        pathname: rawUrl.slice(0, queryIndex) || '/',
        search: rawUrl.slice(queryIndex),
    };
}
function getSanitizedOutgoingUrlAttributes(rawUrl, origin) {
    const hasOrigin = /^[a-z][a-z\d+\-.]*:\/\//i.test(rawUrl);
    try {
        const parsedUrl = new URL(rawUrl, origin !== null && origin !== void 0 ? origin : 'http://localhost');
        const safeOrigin = hasOrigin || origin ? parsedUrl.origin : undefined;
        return getSanitizedUrlAttributesFromParts(safeOrigin, parsedUrl.pathname, parsedUrl.search);
    }
    catch (_a) {
        const { pathname, search } = getFallbackUrlParts(rawUrl);
        return getSanitizedUrlAttributesFromParts(origin, pathname, search);
    }
}
function normalizeProtocol(protocol) {
    return protocol.endsWith(':') ? protocol : `${protocol}:`;
}
function getRequestAgentProtocol(request) {
    const { agent } = request;
    if (!agent || typeof agent === 'boolean') {
        return undefined;
    }
    return getStringValue(agent.protocol);
}
function getOutgoingHttpProtocol(request) {
    var _a;
    const protocol = (_a = getStringValue(request.protocol)) !== null && _a !== void 0 ? _a : getRequestAgentProtocol(request);
    if (!protocol) {
        return 'http:';
    }
    return normalizeProtocol(protocol);
}
function getUrlAuthorityHost(host) {
    try {
        const parsedHost = new URL(`http://${host}`);
        return parsedHost.host;
    }
    catch (_a) {
        if (host.includes(':') && !host.startsWith('[')) {
            return `[${host}]`;
        }
    }
    return host;
}
function getHostWithPort(host, port) {
    const authorityHost = getUrlAuthorityHost(host);
    if (!port) {
        return authorityHost;
    }
    try {
        const parsedHost = new URL(`http://${authorityHost}`);
        if (parsedHost.port) {
            return authorityHost;
        }
    }
    catch (_a) {
        return authorityHost;
    }
    return `${authorityHost}:${port}`;
}
function getOutgoingHttpOrigin(request) {
    const protocol = getOutgoingHttpProtocol(request);
    const host = getStringValue(request.host);
    const port = getStringValue(request.port);
    if (host) {
        return `${protocol}//${getHostWithPort(host, port)}`;
    }
    const hostname = getStringValue(request.hostname);
    const resolvedHostname = hostname !== null && hostname !== void 0 ? hostname : 'localhost';
    return `${protocol}//${getHostWithPort(resolvedHostname, port)}`;
}
function getOutgoingHttpUrl(request) {
    if (request.path) {
        return request.path;
    }
    if (request.href) {
        return request.href;
    }
    const pathname = request.pathname || '/';
    if (!request.search) {
        return pathname;
    }
    const search = request.search.startsWith('?') ? request.search : `?${request.search}`;
    return `${pathname}${search}`;
}
function getSanitizedOutgoingHttpUrlAttributes(request) {
    const requestWithUrlParts = request;
    return getSanitizedOutgoingUrlAttributes(getOutgoingHttpUrl(requestWithUrlParts), getOutgoingHttpOrigin(request));
}
function getSanitizedUndiciUrlAttributes(request) {
    var _a;
    return getSanitizedOutgoingUrlAttributes((_a = request.path) !== null && _a !== void 0 ? _a : '/', request.origin);
}
function getResourceAttributes(config) {
    const attributes = {
        [semanticConventions.ATTR_SERVICE_NAME]: config.serviceName,
    };
    if (config.serviceVersion) {
        attributes[semanticConventions.ATTR_SERVICE_VERSION] = config.serviceVersion;
    }
    return attributes;
}
function createSdk(config) {
    const sdkConfig = {
        resource: resources.resourceFromAttributes(getResourceAttributes(config)),
        instrumentations: [
            new instrumentationHttp.HttpInstrumentation({
                headersToSpanAttributes: {
                    client: { requestHeaders: [], responseHeaders: [] },
                    server: { requestHeaders: [], responseHeaders: [] },
                },
                requestHook: (span, request) => {
                    if (request instanceof http.IncomingMessage) {
                        requestSpans.set(request, span);
                    }
                },
                startIncomingSpanHook: (request) => getSanitizedIncomingUrlAttributes(request, config.healthPath),
                startOutgoingSpanHook: (request) => getSanitizedOutgoingHttpUrlAttributes(request),
                ignoreIncomingRequestHook: (request) => shouldIgnoreIncomingRequest(request, config.healthPath),
            }),
            new instrumentationExpress.ExpressInstrumentation(),
            new instrumentationMongodb.MongoDBInstrumentation(),
            new instrumentationMongoose.MongooseInstrumentation(),
            new instrumentationIoredis.IORedisInstrumentation(),
            new instrumentationUndici.UndiciInstrumentation({
                startSpanHook: (request) => getSanitizedUndiciUrlAttributes(request),
            }),
        ],
    };
    return new sdkNode.NodeSDK(sdkConfig);
}
function getTelemetryRequestSpan(request) {
    return requestSpans.get(request);
}
/**
 * NodeSDK.start has been synchronous in some supported OpenTelemetry versions
 * and promise-returning in others, so the lifecycle wrapper accepts either form.
 */
function startSdk(sdk) {
    return sdk.start();
}
function emitWarning(message) {
    process.emitWarning(message, { code: WARNING_CODE });
}
function getErrorMessage(error) {
    return error instanceof Error ? error.message : String(error);
}
function isControllerEnabled() {
    return status === 'starting' || status === 'started';
}
function makeController() {
    return {
        get enabled() {
            return isControllerEnabled();
        },
        get status() {
            return status;
        },
        shutdown: shutdownTelemetry,
    };
}
function ensureShutdownTaskRegistered() {
    if (shutdownTaskRegistered) {
        return;
    }
    shutdownTaskRegistered = true;
    // Register with the centralized graceful-shutdown coordinator
    // (see ../app/shutdown.ts) rather than attaching SIGTERM/SIGINT
    // listeners directly — signal listener return values are ignored
    // by Node, so a separate signal handler can let the coordinator
    // exit before the async OpenTelemetry flush completes, dropping
    // final spans during pod shutdowns.
    shutdown.registerShutdownTask('telemetry', () => withTimeout(shutdownTelemetry(), SIGNAL_SHUTDOWN_TIMEOUT_MS).catch((error) => {
        emitWarning(`OpenTelemetry shutdown failed: ${getErrorMessage(error)}`);
    }));
}
function withTimeout(promise, timeoutMs) {
    let timeout;
    const timeoutPromise = new Promise((_, reject) => {
        var _a;
        timeout = setTimeout(() => {
            reject(new Error(`timed out after ${timeoutMs}ms`));
        }, timeoutMs);
        (_a = timeout.unref) === null || _a === void 0 ? void 0 : _a.call(timeout);
    });
    return Promise.race([promise, timeoutPromise]).finally(() => {
        if (timeout) {
            clearTimeout(timeout);
        }
    });
}
function initializeTelemetry(env = process.env) {
    if (activeSdk || pendingSdk) {
        return makeController();
    }
    const config = getTelemetryConfig(env);
    if (!config.enabled || isBunRuntime()) {
        status = 'disabled';
        return makeController();
    }
    try {
        const sdk = createSdk(config);
        const result = startSdk(sdk);
        if (result) {
            pendingSdk = sdk;
            status = 'starting';
            const pendingStart = result
                .then(() => {
                if (pendingSdk === sdk) {
                    pendingSdk = undefined;
                    activeSdk = sdk;
                    status = 'started';
                    ensureShutdownTaskRegistered();
                }
            })
                .catch((error) => {
                if (pendingSdk === sdk) {
                    pendingSdk = undefined;
                    status = 'failed';
                    emitWarning(`OpenTelemetry initialization failed: ${getErrorMessage(error)}`);
                }
            });
            startPromise = pendingStart;
            void pendingStart.finally(() => {
                if (startPromise === pendingStart) {
                    startPromise = undefined;
                }
            });
            return makeController();
        }
        activeSdk = sdk;
        status = 'started';
        ensureShutdownTaskRegistered();
        return makeController();
    }
    catch (error) {
        status = 'failed';
        emitWarning(`OpenTelemetry initialization failed: ${getErrorMessage(error)}`);
        return makeController();
    }
}
function performShutdownTelemetry() {
    return shutdown.__awaiter(this, void 0, void 0, function* () {
        if (startPromise) {
            yield startPromise;
        }
        if (!activeSdk) {
            status = status === 'started' ? 'stopped' : status;
            return;
        }
        const sdk = activeSdk;
        try {
            yield sdk.shutdown();
            activeSdk = undefined;
            status = 'stopped';
        }
        catch (error) {
            status = 'started';
            throw error;
        }
    });
}
function shutdownTelemetry() {
    if (!shutdownPromise) {
        shutdownPromise = performShutdownTelemetry().finally(() => {
            shutdownPromise = undefined;
        });
    }
    return shutdownPromise;
}

const CLIENT_CLOSED_REQUEST_STATUS_CODE = 499;
function getUserId(req) {
    var _a;
    return (_a = req.user) === null || _a === void 0 ? void 0 : _a.id;
}
function getTenantId(req) {
    var _a;
    return (_a = req.user) === null || _a === void 0 ? void 0 : _a.tenantId;
}
function isHealthPath(req) {
    return req.path === DEFAULT_HEALTH_PATH;
}
function isApiPath(req) {
    return req.path === '/api' || req.path.startsWith('/api/');
}
function getRoutePath(req) {
    var _a;
    const routePath = (_a = req.route) === null || _a === void 0 ? void 0 : _a.path;
    if (typeof routePath === 'string') {
        return `${req.baseUrl}${routePath}`;
    }
    if (isHealthPath(req)) {
        return '/health';
    }
    if (isApiPath(req)) {
        return '/api/*';
    }
    return 'spa_fallback';
}
function setIdentityAttributes(span, req) {
    const userId = getUserId(req);
    const tenantId = getTenantId(req);
    if (!userId && !tenantId) {
        return;
    }
    const attributes = {};
    if (userId) {
        attributes['enduser.id'] = userId;
    }
    if (tenantId) {
        attributes['librechat.tenant.id'] = tenantId;
    }
    span.setAttributes(attributes);
}
function setCompletionAttributes(span, req, res, aborted = false) {
    const statusCode = aborted ? CLIENT_CLOSED_REQUEST_STATUS_CODE : res.statusCode;
    const routePath = getRoutePath(req);
    const attributes = {
        'http.route': routePath,
        'http.response.status_code': statusCode,
    };
    if (aborted) {
        attributes['librechat.request.aborted'] = true;
    }
    setIdentityAttributes(span, req);
    span.setAttributes(attributes);
    if (aborted || statusCode >= 500) {
        span.setStatus({ code: api.SpanStatusCode.ERROR });
    }
}
function telemetryMiddleware(req, res, next) {
    var _a;
    if (isHealthPath(req)) {
        next();
        return;
    }
    const span = (_a = getTelemetryRequestSpan(req)) !== null && _a !== void 0 ? _a : api.trace.getActiveSpan();
    if (!span) {
        next();
        return;
    }
    span.setAttributes({
        'http.request.method': req.method,
    });
    let completed = false;
    const complete = () => {
        if (completed) {
            return;
        }
        completed = true;
        setCompletionAttributes(span, req, res);
    };
    const close = () => {
        if (completed) {
            return;
        }
        completed = true;
        setCompletionAttributes(span, req, res, !res.writableEnded);
    };
    res.once('finish', complete);
    res.once('close', close);
    next();
}
function telemetryErrorMiddleware(err, req, _res, next) {
    var _a;
    const span = (_a = getTelemetryRequestSpan(req)) !== null && _a !== void 0 ? _a : api.trace.getActiveSpan();
    if (span) {
        const routePath = getRoutePath(req);
        if (err) {
            span.recordException(err instanceof Error ? err : String(err));
        }
        span.setStatus({ code: api.SpanStatusCode.ERROR });
        setIdentityAttributes(span, req);
        span.setAttributes({
            'error.type': getErrorType(err),
            'http.route': routePath,
        });
    }
    next(err);
}
function getErrorType(err) {
    if (err instanceof Error) {
        return err.name || err.constructor.name;
    }
    if (err === null) {
        return 'null';
    }
    return typeof err;
}

const STREAM_SPAN_NAME = 'librechat.sse.stream';
const STREAM_ROUTE = '/api/agents/chat/stream/:streamId';
class SseStreamSpanTelemetry {
    constructor({ isResume, req, res, streamId }) {
        this.startTimeMs = node_perf_hooks.performance.now();
        this.bytesSent = 0;
        this.chunksCount = 0;
        this.ended = false;
        this.errorEventEmitted = false;
        this.finalEventEmitted = false;
        this.finalEventWritten = false;
        this.span = api.trace.getTracer('librechat.telemetry').startSpan(STREAM_SPAN_NAME, {
            kind: api.SpanKind.INTERNAL,
            attributes: {
                'http.request.method': req.method,
                'http.route': STREAM_ROUTE,
                'librechat.stream.id': streamId,
                'librechat.stream.resume': isResume,
                'librechat.stream.route': STREAM_ROUTE,
            },
        }, api.context.active());
        res.once('finish', () => {
            var _a;
            this.end((_a = this.plannedEndReason) !== null && _a !== void 0 ? _a : (this.errorEventEmitted ? 'server_error' : 'done'));
        });
        res.once('close', () => {
            var _a;
            if (res.writableEnded) {
                this.end((_a = this.plannedEndReason) !== null && _a !== void 0 ? _a : (this.errorEventEmitted ? 'server_error' : 'done'));
                return;
            }
            this.span.addEvent('client_aborted');
            this.end('client_aborted');
        });
    }
    recordHeadersFlushed() {
        this.span.addEvent('headers_flushed');
        this.span.setAttribute('librechat.stream.headers_flushed', true);
    }
    recordWrite(payload, options) {
        if (this.ended) {
            return;
        }
        this.chunksCount += 1;
        this.bytesSent += Buffer.byteLength(payload);
        if (this.firstChunkMs === undefined) {
            this.firstChunkMs = node_perf_hooks.performance.now() - this.startTimeMs;
            this.span.addEvent('first_chunk');
            this.span.setAttribute('librechat.stream.time_to_first_chunk_ms', this.firstChunkMs);
        }
        if (options === null || options === void 0 ? void 0 : options.final) {
            this.finalEventWritten = true;
            this.span.addEvent('final_event_written');
        }
    }
    recordFinalEventEmitted() {
        this.finalEventEmitted = true;
        this.plannedEndReason = 'done';
        this.span.addEvent('final_event_emitted');
    }
    recordErrorEventEmitted() {
        var _a;
        this.errorEventEmitted = true;
        (_a = this.plannedEndReason) !== null && _a !== void 0 ? _a : (this.plannedEndReason = 'server_error');
        this.span.addEvent('error_event_emitted');
    }
    recordSubscribeFailed() {
        this.plannedEndReason = 'subscribe_failed';
        this.span.addEvent('subscribe_failed');
    }
    end(reason) {
        if (this.ended) {
            return;
        }
        this.ended = true;
        const attributes = {
            'http.response.body.size': this.bytesSent,
            'librechat.stream.bytes.sent': this.bytesSent,
            'librechat.stream.chunks.count': this.chunksCount,
            'librechat.stream.completed': reason === 'done',
            'librechat.stream.duration_ms': node_perf_hooks.performance.now() - this.startTimeMs,
            'librechat.stream.end_reason': reason,
            'librechat.stream.error_event_emitted': this.errorEventEmitted,
            'librechat.stream.final_event_emitted': this.finalEventEmitted,
            'librechat.stream.final_event_written': this.finalEventWritten,
        };
        if (this.firstChunkMs !== undefined) {
            attributes['librechat.stream.time_to_first_chunk_ms'] = this.firstChunkMs;
        }
        this.span.setAttributes(attributes);
        if (reason !== 'done') {
            this.span.setStatus({ code: api.SpanStatusCode.ERROR });
            this.span.setAttribute('error.type', reason);
        }
        this.span.end();
    }
}
function createSseStreamTelemetry(options) {
    return new SseStreamSpanTelemetry(options);
}

exports.createSseStreamTelemetry = createSseStreamTelemetry;
exports.getTelemetryConfig = getTelemetryConfig;
exports.initializeTelemetry = initializeTelemetry;
exports.shutdownTelemetry = shutdownTelemetry;
exports.telemetryErrorMiddleware = telemetryErrorMiddleware;
exports.telemetryMiddleware = telemetryMiddleware;
//# sourceMappingURL=telemetry.js.map
