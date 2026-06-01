import { Schema } from 'mongoose';

const accessRoleSchema = new Schema({
    accessRoleId: {
        type: String,
        required: true,
        index: true,
    },
    name: {
        type: String,
        required: true,
    },
    description: String,
    resourceType: {
        type: String,
        enum: ['agent', 'project', 'file', 'promptGroup', 'mcpServer', 'remoteAgent', 'skill'],
        required: true,
        default: 'agent',
    },
    permBits: {
        type: Number,
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
}, { timestamps: true });
accessRoleSchema.index({ accessRoleId: 1, tenantId: 1 }, { unique: true });

export { accessRoleSchema as default };
//# sourceMappingURL=accessRole.es.js.map
