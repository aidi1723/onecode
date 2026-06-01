import mongoose, { Schema } from 'mongoose';

const sessionSchema = new Schema({
    refreshTokenHash: {
        type: String,
        required: true,
    },
    expiration: {
        type: Date,
        required: true,
        expires: 0,
    },
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
});

export { sessionSchema as default };
//# sourceMappingURL=session.es.js.map
