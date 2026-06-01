import { EModelEndpoint } from 'librechat-data-provider';
import { azureAssistantsDefaults, assistantsConfigSetup } from './assistants.es.js';
import { agentsConfigSetup } from './agents.es.js';
import { azureConfigSetup } from './azure.es.js';
import { vertexConfigSetup } from './vertex.es.js';

/**
 * Loads custom config endpoints
 * @param [config]
 * @param [agentsDefaults]
 */
const loadEndpoints = (config, agentsDefaults) => {
    var _a;
    const loadedEndpoints = {};
    const endpoints = config === null || config === void 0 ? void 0 : config.endpoints;
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[EModelEndpoint.azureOpenAI]) {
        loadedEndpoints[EModelEndpoint.azureOpenAI] = azureConfigSetup(config);
    }
    if ((_a = endpoints === null || endpoints === void 0 ? void 0 : endpoints[EModelEndpoint.azureOpenAI]) === null || _a === void 0 ? void 0 : _a.assistants) {
        loadedEndpoints[EModelEndpoint.azureAssistants] = azureAssistantsDefaults();
    }
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[EModelEndpoint.azureAssistants]) {
        loadedEndpoints[EModelEndpoint.azureAssistants] = assistantsConfigSetup(config, EModelEndpoint.azureAssistants, loadedEndpoints[EModelEndpoint.azureAssistants]);
    }
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[EModelEndpoint.assistants]) {
        loadedEndpoints[EModelEndpoint.assistants] = assistantsConfigSetup(config, EModelEndpoint.assistants, loadedEndpoints[EModelEndpoint.assistants]);
    }
    loadedEndpoints[EModelEndpoint.agents] = agentsConfigSetup(config, agentsDefaults);
    // Handle Anthropic endpoint with Vertex AI configuration
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[EModelEndpoint.anthropic]) {
        const anthropicConfig = endpoints[EModelEndpoint.anthropic];
        const vertexConfig = vertexConfigSetup(config);
        loadedEndpoints[EModelEndpoint.anthropic] = {
            ...anthropicConfig,
            // If Vertex AI is enabled, use the visible model names from vertex config
            // Otherwise, use the models array from anthropic config
            ...((vertexConfig === null || vertexConfig === void 0 ? void 0 : vertexConfig.modelNames) && { models: vertexConfig.modelNames }),
            // Attach validated Vertex AI config if present
            ...(vertexConfig && { vertexConfig }),
        };
    }
    const endpointKeys = [
        EModelEndpoint.openAI,
        EModelEndpoint.google,
        EModelEndpoint.custom,
        EModelEndpoint.bedrock,
    ];
    endpointKeys.forEach((key) => {
        const currentKey = key;
        if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[currentKey]) {
            loadedEndpoints[currentKey] = endpoints[currentKey];
        }
    });
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints.all) {
        loadedEndpoints.all = endpoints.all;
    }
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints.allowedAddresses) {
        loadedEndpoints.allowedAddresses = endpoints.allowedAddresses;
    }
    return loadedEndpoints;
};

export { loadEndpoints };
//# sourceMappingURL=endpoints.es.js.map
