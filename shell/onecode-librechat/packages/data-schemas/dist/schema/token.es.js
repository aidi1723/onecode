import { Schema } from 'mongoose';

const tokenSchema = new Schema({
    userId: {
        type: Schema.Types.ObjectId,
        required: true,
        ref: 'user',
    },
    email: {
        type: String,
    },
    type: {
        type: String,
    },
    identifier: {
        type: String,
    },
    token: {
        type: String,
        required: true,
    },
    createdAt: {
        type: Date,
        required: true,
        default: Date.now,
    },
    expiresAt: {
        type: Date,
        required: true,
    },
    metadata: {
        type: Map,
        of: Schema.Types.Mixed,
    },
    tenantId: {
        type: String,
        index: true,
    },
});
tokenSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

export { tokenSchema as default };
//# sourceMappingURL=token.es.js.map
