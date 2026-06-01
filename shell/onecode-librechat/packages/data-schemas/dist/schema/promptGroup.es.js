import { Schema } from 'mongoose';
import { Constants } from 'librechat-data-provider';

const promptGroupSchema = new Schema({
    name: {
        type: String,
        required: true,
        index: true,
    },
    numberOfGenerations: {
        type: Number,
        default: 0,
    },
    oneliner: {
        type: String,
        default: '',
    },
    category: {
        type: String,
        default: '',
        index: true,
    },
    productionId: {
        type: Schema.Types.ObjectId,
        ref: 'Prompt',
        required: true,
        index: true,
    },
    author: {
        type: Schema.Types.ObjectId,
        ref: 'User',
        required: true,
        index: true,
    },
    authorName: {
        type: String,
        required: true,
    },
    command: {
        type: String,
        index: true,
        validate: {
            validator: function (v) {
                return v === undefined || v === null || v === '' || /^[a-z0-9-]+$/.test(v);
            },
            message: (props) => { var _a; return `${(_a = props === null || props === void 0 ? void 0 : props.value) !== null && _a !== void 0 ? _a : 'Value'} is not a valid command. Only lowercase alphanumeric characters and hyphens are allowed.`; },
        },
        maxlength: [
            Constants.COMMANDS_MAX_LENGTH,
            `Command cannot be longer than ${Constants.COMMANDS_MAX_LENGTH} characters`,
        ],
    }, // Casting here bypasses the type error for the command field.
    tenantId: {
        type: String,
        index: true,
    },
}, {
    timestamps: true,
});
promptGroupSchema.index({ numberOfGenerations: -1, updatedAt: -1, _id: 1 });

export { promptGroupSchema as default };
//# sourceMappingURL=promptGroup.es.js.map
