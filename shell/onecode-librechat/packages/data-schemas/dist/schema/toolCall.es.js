import mongoose, { Schema } from 'mongoose';

const toolCallSchema = new Schema({
    conversationId: {
        type: String,
        required: true,
    },
    messageId: {
        type: String,
        required: true,
    },
    toolId: {
        type: String,
        required: true,
    },
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    result: {
        type: mongoose.Schema.Types.Mixed,
    },
    attachments: {
        type: mongoose.Schema.Types.Mixed,
    },
    blockIndex: {
        type: Number,
    },
    partIndex: {
        type: Number,
    },
    tenantId: {
        type: String,
        index: true,
    },
    expiredAt: {
        type: Date,
    },
}, { timestamps: true });
toolCallSchema.index({ expiredAt: 1 }, { expireAfterSeconds: 0 });
toolCallSchema.index({ messageId: 1, user: 1, tenantId: 1 });
toolCallSchema.index({ conversationId: 1, user: 1, tenantId: 1 });

export { toolCallSchema as default };
//# sourceMappingURL=toolCall.es.js.map
