import { Schema } from 'mongoose';

const agentCategorySchema = new Schema({
    value: {
        type: String,
        required: true,
        trim: true,
        lowercase: true,
        index: true,
    },
    label: {
        type: String,
        required: true,
        trim: true,
    },
    description: {
        type: String,
        trim: true,
        default: '',
    },
    order: {
        type: Number,
        default: 0,
        index: true,
    },
    isActive: {
        type: Boolean,
        default: true,
        index: true,
    },
    custom: {
        type: Boolean,
        default: false,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});
agentCategorySchema.index({ value: 1, tenantId: 1 }, { unique: true });
agentCategorySchema.index({ isActive: 1, order: 1 });
agentCategorySchema.index({ order: 1, label: 1 });

export { agentCategorySchema as default };
//# sourceMappingURL=agentCategory.es.js.map
