import { Schema } from 'mongoose';

const assistantSchema = new Schema({
    user: {
        type: Schema.Types.ObjectId,
        ref: 'User',
        required: true,
    },
    assistant_id: {
        type: String,
        index: true,
        required: true,
    },
    avatar: {
        type: Schema.Types.Mixed,
        default: undefined,
    },
    conversation_starters: {
        type: [String],
        default: [],
    },
    access_level: {
        type: Number,
    },
    file_ids: { type: [String], default: undefined },
    actions: { type: [String], default: undefined },
    append_current_datetime: {
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

export { assistantSchema as default };
//# sourceMappingURL=assistant.es.js.map
