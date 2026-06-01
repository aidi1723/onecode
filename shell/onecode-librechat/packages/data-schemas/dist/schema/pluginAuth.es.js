import { Schema } from 'mongoose';

const pluginAuthSchema = new Schema({
    authField: {
        type: String,
        required: true,
    },
    value: {
        type: String,
        required: true,
    },
    userId: {
        type: String,
        required: true,
    },
    pluginKey: {
        type: String,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });

export { pluginAuthSchema as default };
//# sourceMappingURL=pluginAuth.es.js.map
