import logger from '../config/winston.es.js';
import { removeNullishValues } from 'librechat-data-provider';

/**
 * Loads and maps the Cloudflare Turnstile configuration.
 *
 * Expected config structure:
 *
 * turnstile:
 *   siteKey: "your-site-key-here"
 *   options:
 *     language: "auto"    // "auto" or an ISO 639-1 language code (e.g. en)
 *     size: "normal"      // Options: "normal", "compact", "flexible", or "invisible"
 *
 * @param config - The loaded custom configuration.
 * @param configDefaults - The custom configuration default values.
 * @returns The mapped Turnstile configuration.
 */
function loadTurnstileConfig(config, configDefaults) {
    var _a, _b;
    const { turnstile: customTurnstile } = config !== null && config !== void 0 ? config : {};
    const { turnstile: defaults } = configDefaults;
    const loadedTurnstile = removeNullishValues({
        siteKey: (_a = customTurnstile === null || customTurnstile === void 0 ? void 0 : customTurnstile.siteKey) !== null && _a !== void 0 ? _a : defaults === null || defaults === void 0 ? void 0 : defaults.siteKey,
        options: (_b = customTurnstile === null || customTurnstile === void 0 ? void 0 : customTurnstile.options) !== null && _b !== void 0 ? _b : defaults === null || defaults === void 0 ? void 0 : defaults.options,
    });
    const enabled = Boolean(loadedTurnstile.siteKey);
    if (enabled) {
        logger.debug('Turnstile is ENABLED with configuration:\n' + JSON.stringify(loadedTurnstile, null, 2));
    }
    else {
        logger.debug('Turnstile is DISABLED (no siteKey provided).');
    }
    return loadedTurnstile;
}

export { loadTurnstileConfig };
//# sourceMappingURL=turnstile.es.js.map
