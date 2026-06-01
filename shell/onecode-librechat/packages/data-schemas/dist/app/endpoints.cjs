'use strict';

var librechatDataProvider = require('librechat-data-provider');
var assistants = require('./assistants.cjs');
var agents = require('./agents.cjs');
var azure = require('./azure.cjs');
var vertex = require('./vertex.cjs');

/**
 * Loads custom config endpoints
 * @param [config]
 * @param [agentsDefaults]
 */
const loadEndpoints = (config, agentsDefaults) => {
    var _a;
    const loadedEndpoints = {};
    const endpoints = config === null || config === void 0 ? void 0 : config.endpoints;
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[librechatDataProvider.EModelEndpoint.azureOpenAI]) {
        loadedEndpoints[librechatDataProvider.EModelEndpoint.azureOpenAI] = azure.azureConfigSetup(config);
    }
    if ((_a = endpoints === null || endpoints === void 0 ? void 0 : endpoints[librechatDataProvider.EModelEndpoint.azureOpenAI]) === null || _a === void 0 ? void 0 : _a.assistants) {
        loadedEndpoints[librechatDataProvider.EModelEndpoint.azureAssistants] = assistants.azureAssistantsDefaults();
    }
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[librechatDataProvider.EModelEndpoint.azureAssistants]) {
        loadedEndpoints[librechatDataProvider.EModelEndpoint.azureAssistants] = assistants.assistantsConfigSetup(config, librechatDataProvider.EModelEndpoint.azureAssistants, loadedEndpoints[librechatDataProvider.EModelEndpoint.azureAssistants]);
    }
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[librechatDataProvider.EModelEndpoint.assistants]) {
        loadedEndpoints[librechatDataProvider.EModelEndpoint.assistants] = assistants.assistantsConfigSetup(config, librechatDataProvider.EModelEndpoint.assistants, loadedEndpoints[librechatDataProvider.EModelEndpoint.assistants]);
    }
    loadedEndpoints[librechatDataProvider.EModelEndpoint.agents] = agents.agentsConfigSetup(config, agentsDefaults);
    // Handle Anthropic endpoint with Vertex AI configuration
    if (endpoints === null || endpoints === void 0 ? void 0 : endpoints[librechatDataProvider.EModelEndpoint.anthropic]) {
        const anthropicConfig = endpoints[librechatDataProvider.EModelEndpoint.anthropic];
        const vertexConfig = vertex.vertexConfigSetup(config);
        loadedEndpoints[librechatDataProvider.EModelEndpoint.anthropic] = {
            ...anthropicConfig,
            // If Vertex AI is enabled, use the visible model names from vertex config
            // Otherwise, use the models array from anthropic config
            ...((vertexConfig === null || vertexConfig === void 0 ? void 0 : vertexConfig.modelNames) && { models: vertexConfig.modelNames }),
            // Attach validated Vertex AI config if present
            ...(vertexConfig && { vertexConfig }),
        };
    }
    const endpointKeys = [
        librechatDataProvider.EModelEndpoint.openAI,
        librechatDataProvider.EModelEndpoint.google,
        librechatDataProvider.EModelEndpoint.custom,
        librechatDataProvider.EModelEndpoint.bedrock,
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

exports.loadEndpoints = loadEndpoints;
//# sourceMappingURL=endpoints.cjs.map
