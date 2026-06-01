import { Schema } from 'mongoose';

const promptSchema = new Schema({
    groupId: {
        type: Schema.Types.ObjectId,
        ref: 'PromptGroup',
        required: true,
        index: true,
    },
    author: {
        type: Schema.Types.ObjectId,
        ref: 'User',
        required: true,
        index: true,
    },
    prompt: {
        type: String,
        required: true,
    },
    type: {
        type: String,
        enum: ['text', 'chat'],
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});
promptSchema.index({ createdAt: 1, updatedAt: 1 });

export { promptSchema as default };
//# sourceMappingURL=prompt.es.js.map
