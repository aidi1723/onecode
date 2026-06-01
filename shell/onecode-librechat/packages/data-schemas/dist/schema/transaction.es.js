import mongoose, { Schema } from 'mongoose';

const transactionSchema = new Schema({
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        index: true,
        required: true,
    },
    conversationId: {
        type: String,
        ref: 'Conversation',
        index: true,
    },
    tokenType: {
        type: String,
        enum: ['prompt', 'completion', 'credits'],
        required: true,
    },
    model: {
        type: String,
        index: true,
    },
    context: {
        type: String,
    },
    valueKey: {
        type: String,
    },
    rate: Number,
    rawAmount: Number,
    tokenValue: Number,
    inputTokens: { type: Number },
    writeTokens: { type: Number },
    readTokens: { type: Number },
    messageId: { type: String },
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});

export { transactionSchema as default };
//# sourceMappingURL=transaction.es.js.map
