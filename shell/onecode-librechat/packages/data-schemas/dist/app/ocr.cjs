'use strict';

var librechatDataProvider = require('librechat-data-provider');

function loadOCRConfig(config) {
    var _a, _b, _c, _d;
    if (!config)
        return;
    const baseURL = (_a = config === null || config === void 0 ? void 0 : config.baseURL) !== null && _a !== void 0 ? _a : '';
    const apiKey = (_b = config === null || config === void 0 ? void 0 : config.apiKey) !== null && _b !== void 0 ? _b : '';
    const mistralModel = (_c = config === null || config === void 0 ? void 0 : config.mistralModel) !== null && _c !== void 0 ? _c : '';
    return {
        apiKey,
        baseURL,
        mistralModel,
        strategy: (_d = config === null || config === void 0 ? void 0 : config.strategy) !== null && _d !== void 0 ? _d : librechatDataProvider.OCRStrategy.MISTRAL_OCR,
    };
}

exports.loadOCRConfig = loadOCRConfig;
//# sourceMappingURL=ocr.cjs.map
