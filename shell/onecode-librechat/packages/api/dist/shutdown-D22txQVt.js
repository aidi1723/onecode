'use strict';

var dataSchemas = require('@librechat/data-schemas');

/******************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */
/* global Reflect, Promise, SuppressedError, Symbol, Iterator */


function __rest(s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
}

function __awaiter(thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
}

function __values(o) {
    var s = typeof Symbol === "function" && Symbol.iterator, m = s && o[s], i = 0;
    if (m) return m.call(o);
    if (o && typeof o.length === "number") return {
        next: function () {
            if (o && i >= o.length) o = void 0;
            return { value: o && o[i++], done: !o };
        }
    };
    throw new TypeError(s ? "Object is not iterable." : "Symbol.iterator is not defined.");
}

function __await(v) {
    return this instanceof __await ? (this.v = v, this) : new __await(v);
}

function __asyncGenerator(thisArg, _arguments, generator) {
    if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
    var g = generator.apply(thisArg, _arguments || []), i, q = [];
    return i = Object.create((typeof AsyncIterator === "function" ? AsyncIterator : Object).prototype), verb("next"), verb("throw"), verb("return", awaitReturn), i[Symbol.asyncIterator] = function () { return this; }, i;
    function awaitReturn(f) { return function (v) { return Promise.resolve(v).then(f, reject); }; }
    function verb(n, f) { if (g[n]) { i[n] = function (v) { return new Promise(function (a, b) { q.push([n, v, a, b]) > 1 || resume(n, v); }); }; if (f) i[n] = f(i[n]); } }
    function resume(n, v) { try { step(g[n](v)); } catch (e) { settle(q[0][3], e); } }
    function step(r) { r.value instanceof __await ? Promise.resolve(r.value.v).then(fulfill, reject) : settle(q[0][2], r); }
    function fulfill(value) { resume("next", value); }
    function reject(value) { resume("throw", value); }
    function settle(f, v) { if (f(v), q.shift(), q.length) resume(q[0][0], q[0][1]); }
}

function __asyncValues(o) {
    if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
    var m = o[Symbol.asyncIterator], i;
    return m ? m.call(o) : (o = typeof __values === "function" ? __values(o) : o[Symbol.iterator](), i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function () { return this; }, i);
    function verb(n) { i[n] = o[n] && function (v) { return new Promise(function (resolve, reject) { v = o[n](v), settle(resolve, reject, v.done, v.value); }); }; }
    function settle(resolve, reject, d, v) { Promise.resolve(v).then(function(v) { resolve({ value: v, done: d }); }, reject); }
}

typeof SuppressedError === "function" ? SuppressedError : function (error, suppressed, message) {
    var e = new Error(message);
    return e.name = "SuppressedError", e.error = error, e.suppressed = suppressed, e;
};

const SHUTDOWN_TIMEOUT_MS = 60000;
const SIGNALS = ['SIGTERM', 'SIGINT', 'SIGQUIT', 'SIGHUP'];
const tasks = [];
let isShuttingDown = false;
let httpServer = null;
/**
 * Register a cleanup task to run after the HTTP server has closed.
 * Tasks run in registration order; if one throws, subsequent tasks
 * and the final exit are not blocked. Use this instead of attaching
 * `process.on('SIGTERM', ...)` handlers directly — multiple competing
 * signal handlers race with the HTTP drain because Node dispatches
 * listeners in registration order and any one of them can call
 * `process.exit` before the HTTP server has finished closing.
 */
function registerShutdownTask(name, fn) {
    tasks.push({ name, fn });
}
/**
 * Wires SIGTERM, SIGINT, SIGQUIT, and SIGHUP to a graceful shutdown
 * sequence: close the HTTP server (stop accepting new connections, let
 * in-flight requests finish), run any tasks registered via
 * `registerShutdownTask`, then `process.exit(0)`. After
 * SHUTDOWN_TIMEOUT_MS the process is force-exited with code 1 — a
 * safety net for long-lived connections such as SSE streams that may
 * not finish in time.
 */
function setupGracefulShutdown(server) {
    httpServer = server;
    for (const signal of SIGNALS) {
        process.on(signal, () => {
            void shutdown(signal);
        });
    }
}
/**
 * @internal Reset module state for tests. Not part of the public API.
 */
function __resetShutdownStateForTests() {
    tasks.length = 0;
    isShuttingDown = false;
    httpServer = null;
}
function shutdown(signal) {
    return __awaiter(this, void 0, void 0, function* () {
        if (isShuttingDown) {
            return;
        }
        isShuttingDown = true;
        dataSchemas.logger.info(`Received ${signal}, draining HTTP server...`);
        const forceExit = setTimeout(() => {
            dataSchemas.logger.warn(`Graceful shutdown exceeded ${SHUTDOWN_TIMEOUT_MS}ms, forcing exit`);
            process.exit(1);
        }, SHUTDOWN_TIMEOUT_MS);
        forceExit.unref();
        let exitCode = 0;
        try {
            yield closeHttpServer();
        }
        catch (err) {
            dataSchemas.logger.error('Error closing HTTP server during graceful shutdown:', err);
            exitCode = 1;
        }
        for (const task of tasks) {
            try {
                dataSchemas.logger.info(`Running shutdown task: ${task.name}`);
                yield task.fn();
            }
            catch (err) {
                dataSchemas.logger.error(`Shutdown task "${task.name}" failed:`, err);
            }
        }
        clearTimeout(forceExit);
        dataSchemas.logger.info('Graceful shutdown complete, exiting');
        process.exit(exitCode);
    });
}
function closeHttpServer() {
    return new Promise((resolve, reject) => {
        if (!httpServer || !httpServer.listening) {
            // SIGTERM can arrive during startup before the listen socket is open,
            // in which case there is nothing to drain. Node also surfaces this as
            // an ERR_SERVER_NOT_RUNNING error in the close callback — treated
            // below as a successful close so a routine shutdown doesn't trip
            // orchestrator restart/backoff with exit code 1.
            resolve();
            return;
        }
        httpServer.close((err) => {
            if (!err || err.code === 'ERR_SERVER_NOT_RUNNING') {
                resolve();
                return;
            }
            reject(err);
        });
    });
}

exports.__asyncGenerator = __asyncGenerator;
exports.__asyncValues = __asyncValues;
exports.__await = __await;
exports.__awaiter = __awaiter;
exports.__resetShutdownStateForTests = __resetShutdownStateForTests;
exports.__rest = __rest;
exports.registerShutdownTask = registerShutdownTask;
exports.setupGracefulShutdown = setupGracefulShutdown;
//# sourceMappingURL=shutdown-D22txQVt.js.map
