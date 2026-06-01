import { removeNullishValues } from 'librechat-data-provider';
import { isMemoryEnabled } from './memory.es.js';

/**
 * Loads the default interface object.
 * @param params - The loaded custom configuration.
 * @param params.config - The loaded custom configuration.
 * @param params.configDefaults - The custom configuration default values.
 * @returns default interface object.
 */
async function loadDefaultInterface({ config, configDefaults, }) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p;
    const { interface: interfaceConfig } = config !== null && config !== void 0 ? config : {};
    const { interface: defaults } = configDefaults;
    const hasModelSpecs = ((_c = (_b = (_a = config === null || config === void 0 ? void 0 : config.modelSpecs) === null || _a === void 0 ? void 0 : _a.list) === null || _b === void 0 ? void 0 : _b.length) !== null && _c !== void 0 ? _c : 0) > 0;
    const includesAddedEndpoints = ((_f = (_e = (_d = config === null || config === void 0 ? void 0 : config.modelSpecs) === null || _d === void 0 ? void 0 : _d.addedEndpoints) === null || _e === void 0 ? void 0 : _e.length) !== null && _f !== void 0 ? _f : 0) > 0;
    const memoryConfig = config === null || config === void 0 ? void 0 : config.memory;
    const memoryEnabled = isMemoryEnabled(memoryConfig);
    /** Only disable memories if memory config is present and explicitly disabled */
    const shouldDisableMemories = memoryConfig && !memoryEnabled;
    const loadedInterface = removeNullishValues({
        // UI elements - use schema defaults
        modelSelect: (_g = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.modelSelect) !== null && _g !== void 0 ? _g : (hasModelSpecs ? includesAddedEndpoints : defaults.modelSelect),
        parameters: (_h = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.parameters) !== null && _h !== void 0 ? _h : (hasModelSpecs ? false : defaults.parameters),
        presets: (_j = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.presets) !== null && _j !== void 0 ? _j : (hasModelSpecs ? false : defaults.presets),
        privacyPolicy: (_k = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.privacyPolicy) !== null && _k !== void 0 ? _k : defaults.privacyPolicy,
        termsOfService: (_l = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.termsOfService) !== null && _l !== void 0 ? _l : defaults.termsOfService,
        mcpServers: (_m = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.mcpServers) !== null && _m !== void 0 ? _m : defaults.mcpServers,
        customWelcome: (_o = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.customWelcome) !== null && _o !== void 0 ? _o : defaults.customWelcome,
        autoSubmitFromUrl: (_p = interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.autoSubmitFromUrl) !== null && _p !== void 0 ? _p : defaults.autoSubmitFromUrl,
        // Permissions and related settings - only include if explicitly configured
        bookmarks: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.bookmarks,
        memories: shouldDisableMemories ? false : interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.memories,
        prompts: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.prompts,
        multiConvo: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.multiConvo,
        agents: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.agents,
        temporaryChat: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.temporaryChat,
        temporaryChatRetention: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.temporaryChatRetention,
        retentionMode: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.retentionMode,
        runCode: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.runCode,
        webSearch: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.webSearch,
        fileSearch: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.fileSearch,
        fileCitations: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.fileCitations,
        peoplePicker: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.peoplePicker,
        marketplace: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.marketplace,
        remoteAgents: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.remoteAgents,
        skills: interfaceConfig === null || interfaceConfig === void 0 ? void 0 : interfaceConfig.skills,
    });
    return loadedInterface;
}

export { loadDefaultInterface };
//# sourceMappingURL=interface.es.js.map
