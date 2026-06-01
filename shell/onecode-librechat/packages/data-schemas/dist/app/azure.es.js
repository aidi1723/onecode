import logger from '../config/winston.es.js';
import { EModelEndpoint, validateAzureGroups, mapModelToAzureConfig } from 'librechat-data-provider';

/**
 * Sets up the Azure OpenAI configuration from the config (`librechat.yaml`) file.
 * @param config - The loaded custom configuration.
 * @returns The Azure OpenAI configuration.
 */
function azureConfigSetup(config) {
    var _a, _b, _c;
    const azureConfig = (_a = config.endpoints) === null || _a === void 0 ? void 0 : _a[EModelEndpoint.azureOpenAI];
    if (!azureConfig) {
        throw new Error('Azure OpenAI configuration is missing.');
    }
    const { groups, ...azureConfiguration } = azureConfig;
    const { isValid, modelNames, modelGroupMap, groupMap, errors } = validateAzureGroups(groups);
    if (!isValid) {
        const errorString = errors.join('\n');
        const errorMessage = 'Invalid Azure OpenAI configuration:\n' + errorString;
        logger.error(errorMessage);
        throw new Error(errorMessage);
    }
    const assistantModels = [];
    const assistantGroups = new Set();
    for (const modelName of modelNames) {
        mapModelToAzureConfig({ modelName, modelGroupMap, groupMap });
        const groupName = (_b = modelGroupMap === null || modelGroupMap === void 0 ? void 0 : modelGroupMap[modelName]) === null || _b === void 0 ? void 0 : _b.group;
        const modelGroup = groupMap === null || groupMap === void 0 ? void 0 : groupMap[groupName];
        const supportsAssistants = (modelGroup === null || modelGroup === void 0 ? void 0 : modelGroup.assistants) || ((_c = modelGroup === null || modelGroup === void 0 ? void 0 : modelGroup[modelName]) === null || _c === void 0 ? void 0 : _c.assistants);
        if (supportsAssistants) {
            assistantModels.push(modelName);
            if (!assistantGroups.has(groupName)) {
                assistantGroups.add(groupName);
            }
        }
    }
    if (azureConfiguration.assistants && assistantModels.length === 0) {
        throw new Error('No Azure models are configured to support assistants. Please remove the `assistants` field or configure at least one model to support assistants.');
    }
    if (azureConfiguration.assistants &&
        process.env.ENDPOINTS &&
        !process.env.ENDPOINTS.includes(EModelEndpoint.azureAssistants)) {
        logger.warn(`Azure Assistants are configured, but the endpoint will not be accessible as it's not included in the ENDPOINTS environment variable.
      Please add the value "${EModelEndpoint.azureAssistants}" to the ENDPOINTS list if expected.`);
    }
    return {
        errors,
        isValid,
        groupMap,
        modelNames,
        modelGroupMap,
        assistantModels,
        assistantGroups: Array.from(assistantGroups),
        ...azureConfiguration,
    };
}

export { azureConfigSetup };
//# sourceMappingURL=azure.es.js.map
