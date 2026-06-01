import { EModelEndpoint, agentsEndpointSchema } from 'librechat-data-provider';

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
    const agentsConfig = (_a = config === null || config === void 0 ? void 0 : config.endpoints) === null || _a === void 0 ? void 0 : _a[EModelEndpoint.agents];
    if (!agentsConfig) {
        return defaultConfig || agentsEndpointSchema.parse({});
    }
    const parsedConfig = agentsEndpointSchema.parse(agentsConfig);
    return parsedConfig;
}

export { agentsConfigSetup };
//# sourceMappingURL=agents.es.js.map
