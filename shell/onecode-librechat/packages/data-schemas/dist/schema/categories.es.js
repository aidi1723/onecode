import { Schema } from 'mongoose';

const categoriesSchema = new Schema({
    label: {
        type: String,
        required: true,
    },
    value: {
        type: String,
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
});
categoriesSchema.index({ label: 1, tenantId: 1 }, { unique: true });
categoriesSchema.index({ value: 1, tenantId: 1 }, { unique: true });

export { categoriesSchema as default };
//# sourceMappingURL=categories.es.js.map
