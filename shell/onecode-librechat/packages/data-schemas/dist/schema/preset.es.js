import { Schema } from 'mongoose';
import { conversationPreset } from './defaults.es.js';

const presetSchema = new Schema({
    presetId: {
        type: String,
        required: true,
        index: true,
    },
    title: {
        type: String,
        default: 'New Chat',
        meiliIndex: true,
    },
    user: {
        type: String,
        default: null,
    },
    defaultPreset: {
        type: Boolean,
    },
    order: {
        type: Number,
    },
    ...conversationPreset,
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
presetSchema.index({ presetId: 1, tenantId: 1 }, { unique: true });

export { presetSchema as default };
//# sourceMappingURL=preset.es.js.map
