'use strict';

var mongoose = require('mongoose');

// Define the Auth sub-schema with type-safety.
const AuthSchema = new mongoose.Schema({
    authorization_type: { type: String },
    custom_auth_header: { type: String },
    type: { type: String, enum: ['service_http', 'oauth', 'none'] },
    authorization_content_type: { type: String },
    authorization_url: { type: String },
    client_url: { type: String },
    scope: { type: String },
    token_exchange_method: { type: String, enum: ['default_post', 'basic_auth_header', null] },
}, { _id: false });
const Action = new mongoose.Schema({
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        index: true,
        required: true,
    },
    action_id: {
        type: String,
        index: true,
        required: true,
    },
    type: {
        type: String,
        default: 'action_prototype',
    },
    settings: mongoose.Schema.Types.Mixed,
    agent_id: String,
    assistant_id: String,
    metadata: {
        api_key: String,
        auth: AuthSchema,
        domain: {
            type: String,
            required: true,
        },
        privacy_policy_url: String,
        raw_spec: String,
        oauth_client_id: String,
        oauth_client_secret: String,
    },
    tenantId: {
        type: String,
        index: true,
    },
});

module.exports = Action;
//# sourceMappingURL=action.cjs.map
