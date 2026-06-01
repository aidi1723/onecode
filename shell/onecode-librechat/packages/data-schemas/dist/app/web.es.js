import { SafeSearchTypes } from 'librechat-data-provider';

const webSearchAuth = {
    providers: {
        serper: {
            serperApiKey: 1,
        },
        searxng: {
            searxngInstanceUrl: 1,
            /** Optional (0) */
            searxngApiKey: 0,
        },
        tavily: {
            tavilyApiKey: 1,
            tavilySearchUrl: 0,
        },
    },
    scrapers: {
        firecrawl: {
            firecrawlApiKey: 1,
            /** Optional (0) */
            firecrawlApiUrl: 0,
            firecrawlVersion: 0,
        },
        serper: {
            serperApiKey: 1,
        },
        tavily: {
            tavilyApiKey: 1,
            tavilyExtractUrl: 0,
        },
    },
    rerankers: {
        jina: {
            jinaApiKey: 1,
            /** Optional (0) */
            jinaApiUrl: 0,
        },
        cohere: { cohereApiKey: 1 },
    },
};
/**
 * Extracts all unique API keys from the webSearchAuth configuration object
 */
function getWebSearchKeys() {
    const keysSet = new Set();
    // Iterate through each category (providers, scrapers, rerankers)
    for (const category of Object.keys(webSearchAuth)) {
        const categoryObj = webSearchAuth[category];
        // Iterate through each service within the category
        for (const service of Object.keys(categoryObj)) {
            const serviceObj = categoryObj[service];
            // Extract the API keys from the service and add to set for deduplication
            for (const key of Object.keys(serviceObj)) {
                keysSet.add(key);
            }
        }
    }
    return Array.from(keysSet);
}
const webSearchKeys = getWebSearchKeys();
function loadWebSearchConfig(config) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o;
    const serperApiKey = (_a = config === null || config === void 0 ? void 0 : config.serperApiKey) !== null && _a !== void 0 ? _a : '${SERPER_API_KEY}';
    const searxngInstanceUrl = (_b = config === null || config === void 0 ? void 0 : config.searxngInstanceUrl) !== null && _b !== void 0 ? _b : '${SEARXNG_INSTANCE_URL}';
    const searxngApiKey = (_c = config === null || config === void 0 ? void 0 : config.searxngApiKey) !== null && _c !== void 0 ? _c : '${SEARXNG_API_KEY}';
    const firecrawlApiKey = (_d = config === null || config === void 0 ? void 0 : config.firecrawlApiKey) !== null && _d !== void 0 ? _d : '${FIRECRAWL_API_KEY}';
    const firecrawlApiUrl = (_e = config === null || config === void 0 ? void 0 : config.firecrawlApiUrl) !== null && _e !== void 0 ? _e : '${FIRECRAWL_API_URL}';
    const firecrawlVersion = (_f = config === null || config === void 0 ? void 0 : config.firecrawlVersion) !== null && _f !== void 0 ? _f : '${FIRECRAWL_VERSION}';
    const tavilyApiKey = (_g = config === null || config === void 0 ? void 0 : config.tavilyApiKey) !== null && _g !== void 0 ? _g : '${TAVILY_API_KEY}';
    const tavilySearchUrl = (_h = config === null || config === void 0 ? void 0 : config.tavilySearchUrl) !== null && _h !== void 0 ? _h : '${TAVILY_SEARCH_URL}';
    const tavilyExtractUrl = (_j = config === null || config === void 0 ? void 0 : config.tavilyExtractUrl) !== null && _j !== void 0 ? _j : '${TAVILY_EXTRACT_URL}';
    const jinaApiKey = (_k = config === null || config === void 0 ? void 0 : config.jinaApiKey) !== null && _k !== void 0 ? _k : '${JINA_API_KEY}';
    const jinaApiUrl = (_l = config === null || config === void 0 ? void 0 : config.jinaApiUrl) !== null && _l !== void 0 ? _l : '${JINA_API_URL}';
    const cohereApiKey = (_m = config === null || config === void 0 ? void 0 : config.cohereApiKey) !== null && _m !== void 0 ? _m : '${COHERE_API_KEY}';
    const safeSearch = (_o = config === null || config === void 0 ? void 0 : config.safeSearch) !== null && _o !== void 0 ? _o : SafeSearchTypes.MODERATE;
    const rerankerType = config === null || config === void 0 ? void 0 : config.rerankerType;
    return {
        ...config, // Preserve provider-specific option blocks such as firecrawlOptions and tavilySearchOptions.
        safeSearch,
        jinaApiKey,
        jinaApiUrl,
        cohereApiKey,
        serperApiKey,
        searxngApiKey,
        tavilyApiKey,
        tavilySearchUrl,
        tavilyExtractUrl,
        firecrawlApiKey,
        firecrawlApiUrl,
        firecrawlVersion,
        searxngInstanceUrl,
        rerankerType,
    };
}

export { getWebSearchKeys, loadWebSearchConfig, webSearchAuth, webSearchKeys };
//# sourceMappingURL=web.es.js.map
