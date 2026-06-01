'use strict';

var winston = require('../config/winston.cjs');
var librechatDataProvider = require('librechat-data-provider');

/**
 * Default Vertex AI models available through Google Cloud
 * These are the standard Anthropic model names as served by Vertex AI
 */
const defaultVertexModels = [
    'claude-sonnet-4-6',
    'claude-3-7-sonnet-20250219',
    'claude-3-5-sonnet-v2@20241022',
    'claude-3-5-sonnet@20240620',
    'claude-3-5-haiku@20241022',
    'claude-3-opus@20240229',
    'claude-3-haiku@20240307',
];
/**
 * Processes models configuration and creates deployment name mapping
 * Similar to Azure's model mapping logic
 * @param models - The models configuration (can be array or object)
 * @param defaultDeploymentName - Optional default deployment name
 * @returns Object containing modelNames array and modelDeploymentMap
 */
function processVertexModels(models, defaultDeploymentName) {
    const modelNames = [];
    const modelDeploymentMap = {};
    if (!models) {
        // No models specified, use defaults
        for (const model of defaultVertexModels) {
            modelNames.push(model);
            modelDeploymentMap[model] = model; // Default: model name = deployment name
        }
        return { modelNames, modelDeploymentMap };
    }
    if (Array.isArray(models)) {
        // Legacy format: simple array of model names
        for (const modelName of models) {
            modelNames.push(modelName);
            // If a default deployment name is provided, use it for all models
            // Otherwise, model name is the deployment name
            modelDeploymentMap[modelName] = defaultDeploymentName || modelName;
        }
    }
    else {
        // New format: object with model names as keys and config as values
        for (const [modelName, modelConfig] of Object.entries(models)) {
            modelNames.push(modelName);
            if (typeof modelConfig === 'boolean') {
                // Model is set to true/false - use default deployment name or model name
                modelDeploymentMap[modelName] = defaultDeploymentName || modelName;
            }
            else if (modelConfig === null || modelConfig === void 0 ? void 0 : modelConfig.deploymentName) {
                // Model has its own deployment name specified
                modelDeploymentMap[modelName] = modelConfig.deploymentName;
            }
            else {
                // Model is an object but no deployment name - use default or model name
                modelDeploymentMap[modelName] = defaultDeploymentName || modelName;
            }
        }
    }
    return { modelNames, modelDeploymentMap };
}
/**
 * Validates and processes Vertex AI configuration
 * @param vertexConfig - The Vertex AI configuration object
 * @returns Validated configuration with errors if any
 */
function validateVertexConfig(vertexConfig) {
    if (!vertexConfig) {
        return null;
    }
    const errors = [];
    // Extract and validate environment variables
    // projectId is optional - will be auto-detected from service key if not provided
    const projectId = vertexConfig.projectId ? librechatDataProvider.extractEnvVariable(vertexConfig.projectId) : undefined;
    const region = librechatDataProvider.extractEnvVariable(vertexConfig.region || 'us-east5');
    const serviceKeyFile = vertexConfig.serviceKeyFile
        ? librechatDataProvider.extractEnvVariable(vertexConfig.serviceKeyFile)
        : undefined;
    const defaultDeploymentName = vertexConfig.deploymentName
        ? librechatDataProvider.extractEnvVariable(vertexConfig.deploymentName)
        : undefined;
    // Check for unresolved environment variables
    if (projectId && librechatDataProvider.envVarRegex.test(projectId)) {
        errors.push(`Vertex AI projectId environment variable "${vertexConfig.projectId}" was not found.`);
    }
    if (librechatDataProvider.envVarRegex.test(region)) {
        errors.push(`Vertex AI region environment variable "${vertexConfig.region}" was not found.`);
    }
    if (serviceKeyFile && librechatDataProvider.envVarRegex.test(serviceKeyFile)) {
        errors.push(`Vertex AI serviceKeyFile environment variable "${vertexConfig.serviceKeyFile}" was not found.`);
    }
    if (defaultDeploymentName && librechatDataProvider.envVarRegex.test(defaultDeploymentName)) {
        errors.push(`Vertex AI deploymentName environment variable "${vertexConfig.deploymentName}" was not found.`);
    }
    // Process models and create deployment mapping
    const { modelNames, modelDeploymentMap } = processVertexModels(vertexConfig.models, defaultDeploymentName);
    // Note: projectId is optional - if not provided, it will be auto-detected from the service key file
    const isValid = errors.length === 0;
    return {
        enabled: vertexConfig.enabled !== false,
        projectId,
        region,
        serviceKeyFile,
        deploymentName: defaultDeploymentName,
        models: vertexConfig.models,
        modelNames,
        modelDeploymentMap,
        isValid,
        errors,
    };
}
/**
 * Sets up the Vertex AI configuration from the config (`librechat.yaml`) file.
 * Similar to azureConfigSetup, this processes and validates the Vertex AI configuration.
 * @param config - The loaded custom configuration.
 * @returns The validated Vertex AI configuration or null if not configured.
 */
function vertexConfigSetup(config) {
    var _a, _b;
    const anthropicConfig = (_a = config.endpoints) === null || _a === void 0 ? void 0 : _a[librechatDataProvider.EModelEndpoint.anthropic];
    if (!(anthropicConfig === null || anthropicConfig === void 0 ? void 0 : anthropicConfig.vertex)) {
        return null;
    }
    const vertexConfig = anthropicConfig.vertex;
    // Skip if explicitly disabled (enabled: false)
    // When vertex config exists, it's enabled by default unless explicitly set to false
    if (vertexConfig.enabled === false) {
        return null;
    }
    const validatedConfig = validateVertexConfig(vertexConfig);
    if (!validatedConfig) {
        return null;
    }
    if (!validatedConfig.isValid) {
        const errorString = validatedConfig.errors.join('\n');
        const errorMessage = 'Invalid Vertex AI configuration:\n' + errorString;
        winston.error(errorMessage);
        throw new Error(errorMessage);
    }
    winston.info('Vertex AI configuration loaded successfully', {
        projectId: validatedConfig.projectId,
        region: validatedConfig.region,
        modelCount: ((_b = validatedConfig.modelNames) === null || _b === void 0 ? void 0 : _b.length) || 0,
        models: validatedConfig.modelNames,
    });
    return validatedConfig;
}

exports.defaultVertexModels = defaultVertexModels;
exports.validateVertexConfig = validateVertexConfig;
exports.vertexConfigSetup = vertexConfigSetup;
//# sourceMappingURL=vertex.cjs.map
