import { Schema } from 'mongoose';

const conversationTag = new Schema({
    tag: {
        type: String,
        index: true,
    },
    user: {
        type: String,
        index: true,
    },
    description: {
        type: String,
        index: true,
    },
    count: {
        type: Number,
        default: 0,
    },
    position: {
        type: Number,
        default: 0,
        index: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
// Create a compound index on tag and user with unique constraint.
conversationTag.index({ tag: 1, user: 1, tenantId: 1 }, { unique: true });

export { conversationTag as default };
//# sourceMappingURL=conversationTag.es.js.map
