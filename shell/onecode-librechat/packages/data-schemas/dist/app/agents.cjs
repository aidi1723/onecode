'use strict';

var librechatDataProvider = require('librechat-data-provider');

/**
 * Sets up the Agents configuration from the config (`librechat.yaml`) file.
 * If no agents config is defined, uses the provided defaults or parses empty object.
 *
 * @param config - The loaded custom configuration.
 * @param [defaultConfig] - Default configuration from getConfigDefaults.
 * @returns The Agents endpoint configuration.
 */
function agentsConfigSetup(config, defaultConfig) {
    var _a;
    const agentsConfig = (_a = config === null || config === void 0 ? void 0 : config.endpoints) === null || _a === void 0 ? void 0 : _a[librechatDataProvider.EModelEndpoint.agents];
    if (!agentsConfig) {
        return defaultConfig || librechatDataProvider.agentsEndpointSchema.parse({});
    }
    const parsedConfig = librechatDataProvider.agentsEndpointSchema.parse(agentsConfig);
    return parsedConfig;
}

exports.agentsConfigSetup = agentsConfigSetup;
//# sourceMappingURL=agents.cjs.map
