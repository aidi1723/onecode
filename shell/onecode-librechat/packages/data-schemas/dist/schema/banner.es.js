import { Schema } from 'mongoose';

const bannerSchema = new Schema({
    bannerId: {
        type: String,
        required: true,
    },
    message: {
        type: String,
        required: true,
    },
    displayFrom: {
        type: Date,
        required: true,
        default: Date.now,
    },
    displayTo: {
        type: Date,
    },
    type: {
        type: String,
        enum: ['banner', 'popup'],
        default: 'banner',
    },
    isPublic: {
        type: Boolean,
        default: false,
    },
    persistable: {
        type: Boolean,
        default: false,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });

export { bannerSchema as default };
//# sourceMappingURL=banner.es.js.map
