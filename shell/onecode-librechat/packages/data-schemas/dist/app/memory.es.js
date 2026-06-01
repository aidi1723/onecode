import { memorySchema } from 'librechat-data-provider';
import logger from '../config/winston.es.js';

const hasValidAgent = (agent) => !!agent &&
    (('id' in agent && !!agent.id) ||
        ('provider' in agent && 'model' in agent && !!agent.provider && !!agent.model));
const isDisabled = (config) => !config || config.disabled === true;
function loadMemoryConfig(config) {
    var _a, _b;
    if (!config)
        return undefined;
    if (isDisabled(config))
        return config;
    if (hasValidAgent(config.agent) && ((_a = config.agent) === null || _a === void 0 ? void 0 : _a.enabled) == null) {
        logger.warn('[memory] Agent config detected without explicit `enabled: true`. Automatic memory extraction is now opt-in. Add `memory.agent.enabled: true` to keep automatic memory updates.');
    }
    const charLimit = (_b = memorySchema.shape.charLimit.safeParse(config.charLimit).data) !== null && _b !== void 0 ? _b : 10000;
    return { ...config, charLimit };
}
function isMemoryEnabled(config) {
    return !isDisabled(config);
}
function isMemoryAgentEnabled(config) {
    var _a;
    if (!isMemoryEnabled(config))
        return false;
    return ((_a = config === null || config === void 0 ? void 0 : config.agent) === null || _a === void 0 ? void 0 : _a.enabled) === true && hasValidAgent(config.agent);
}

export { isMemoryAgentEnabled, isMemoryEnabled, loadMemoryConfig };
//# sourceMappingURL=memory.es.js.map
