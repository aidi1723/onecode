import { getConfigDefaults, EModelEndpoint, summarizationConfigSchema } from 'librechat-data-provider';
import { loadDefaultInterface } from './interface.es.js';
import { loadTurnstileConfig } from './turnstile.es.js';
import { agentsConfigSetup } from './agents.es.js';
import { loadWebSearchConfig } from './web.es.js';
import { processModelSpecs } from './specs.es.js';
import { loadMemoryConfig } from './memory.es.js';
import { loadEndpoints } from './endpoints.es.js';
import { loadOCRConfig } from './ocr.es.js';
import logger from '../config/winston.es.js';

function loadSummarizationConfig(config) {
    const raw = config.summarization;
    if (!raw || typeof raw !== 'object') {
        return undefined;
    }
    if (raw.trigger &&
        typeof raw.trigger === 'object' &&
        raw.trigger.type === 'token_count') {
        logger.warn("[AppService] `summarization.trigger.type: 'token_count'` is no longer supported. " +
            "Use 'token_ratio' (0-1), 'remaining_tokens' (positive integer), or " +
            "'messages_to_refine' (positive integer). Your `summarization` config will be " +
            'ignored and summarization will fall back to self-summarize defaults (the ' +
            "agent's own provider/model, fires on every pruning event) until this is " +
            'corrected.');
        return undefined;
    }
    const parsed = summarizationConfigSchema.safeParse(raw);
    if (!parsed.success) {
        logger.warn('[AppService] Invalid summarization config', parsed.error.flatten());
        return undefined;
    }
    return {
        ...parsed.data,
        enabled: parsed.data.enabled !== false,
    };
}
/**
 * Loads custom config and initializes app-wide variables.
 * @function AppService
 */
const AppService = async (params) => {
    var _a, _b, _c, _d, _e, _f;
    const { config, paths, systemTools } = params || {};
    if (!config) {
        throw new Error('Config is required');
    }
    const configDefaults = getConfigDefaults();
    const ocr = loadOCRConfig(config.ocr);
    const webSearch = loadWebSearchConfig(config.webSearch);
    const memory = loadMemoryConfig(config.memory);
    const summarization = loadSummarizationConfig(config);
    const filteredTools = config.filteredTools;
    const includedTools = config.includedTools;
    const fileStrategy = ((_a = config.fileStrategy) !== null && _a !== void 0 ? _a : configDefaults.fileStrategy);
    const startBalance = process.env.START_BALANCE;
    const balance = (_b = config.balance) !== null && _b !== void 0 ? _b : {
        enabled: ((_c = process.env.CHECK_BALANCE) === null || _c === void 0 ? void 0 : _c.toLowerCase().trim()) === 'true',
        startBalance: startBalance ? parseInt(startBalance, 10) : undefined,
    };
    const transactions = (_d = config.transactions) !== null && _d !== void 0 ? _d : configDefaults.transactions;
    const imageOutputType = (_e = config === null || config === void 0 ? void 0 : config.imageOutputType) !== null && _e !== void 0 ? _e : configDefaults.imageOutputType;
    process.env.CDN_PROVIDER = fileStrategy;
    const availableTools = systemTools;
    const mcpServersConfig = config.mcpServers || null;
    const mcpSettings = config.mcpSettings || null;
    const actions = config.actions;
    const registration = (_f = config.registration) !== null && _f !== void 0 ? _f : configDefaults.registration;
    const interfaceConfig = await loadDefaultInterface({ config, configDefaults });
    const turnstileConfig = loadTurnstileConfig(config, configDefaults);
    const speech = config.speech;
    const defaultConfig = {
        ocr,
        paths,
        config,
        memory,
        speech,
        balance,
        actions,
        webSearch,
        mcpSettings,
        transactions,
        fileStrategy,
        registration,
        filteredTools,
        includedTools,
        summarization,
        availableTools,
        imageOutputType,
        interfaceConfig,
        turnstileConfig,
        mcpConfig: mcpServersConfig,
        fileStrategies: config.fileStrategies,
        cloudfront: config.cloudfront,
    };
    const agentsDefaults = agentsConfigSetup(config);
    if (!Object.keys(config).length) {
        const appConfig = {
            ...defaultConfig,
            endpoints: {
                [EModelEndpoint.agents]: agentsDefaults,
            },
        };
        return appConfig;
    }
    const loadedEndpoints = loadEndpoints(config, agentsDefaults);
    const appConfig = {
        ...defaultConfig,
        fileConfig: config === null || config === void 0 ? void 0 : config.fileConfig,
        secureImageLinks: config === null || config === void 0 ? void 0 : config.secureImageLinks,
        modelSpecs: processModelSpecs(config === null || config === void 0 ? void 0 : config.endpoints, config.modelSpecs, interfaceConfig),
        endpoints: loadedEndpoints,
    };
    return appConfig;
};

export { AppService, loadSummarizationConfig };
//# sourceMappingURL=service.es.js.map
