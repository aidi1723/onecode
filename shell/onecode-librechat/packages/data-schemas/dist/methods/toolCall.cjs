'use strict';

function createToolCallMethods(mongoose) {
    /**
     * Create a new tool call
     */
    async function createToolCall(toolCallData) {
        try {
            const ToolCall = mongoose.models.ToolCall;
            return await ToolCall.create(toolCallData);
        }
        catch (error) {
            throw new Error(`Error creating tool call: ${error.message}`);
        }
    }
    /**
     * Get a tool call by ID
     */
    async function getToolCallById(id) {
        try {
            const ToolCall = mongoose.models.ToolCall;
            return await ToolCall.findById(id).lean();
        }
        catch (error) {
            throw new Error(`Error fetching tool call: ${error.message}`);
        }
    }
    /**
     * Get tool calls by message ID and user
     */
    async function getToolCallsByMessage(messageId, userId) {
        try {
            const ToolCall = mongoose.models.ToolCall;
            return await ToolCall.find({ messageId, user: userId }).lean();
        }
        catch (error) {
            throw new Error(`Error fetching tool calls: ${error.message}`);
        }
    }
    /**
     * Get tool calls by conversation ID and user
     */
    async function getToolCallsByConvo(conversationId, userId) {
        try {
            const ToolCall = mongoose.models.ToolCall;
            return await ToolCall.find({ conversationId, user: userId }).lean();
        }
        catch (error) {
            throw new Error(`Error fetching tool calls: ${error.message}`);
        }
    }
    /**
     * Update a tool call
     */
    async function updateToolCall(id, updateData) {
        try {
            const ToolCall = mongoose.models.ToolCall;
            return await ToolCall.findByIdAndUpdate(id, updateData, { new: true }).lean();
        }
        catch (error) {
            throw new Error(`Error updating tool call: ${error.message}`);
        }
    }
    /**
     * Delete tool calls by user and optionally conversation
     */
    async function deleteToolCalls(userId, conversationId) {
        try {
            const ToolCall = mongoose.models.ToolCall;
            const query = { user: userId };
            if (conversationId) {
                query.conversationId = conversationId;
            }
            return await ToolCall.deleteMany(query);
        }
        catch (error) {
            throw new Error(`Error deleting tool call: ${error.message}`);
        }
    }
    return {
        createToolCall,
        updateToolCall,
        deleteToolCalls,
        getToolCallById,
        getToolCallsByConvo,
        getToolCallsByMessage,
    };
}

exports.createToolCallMethods = createToolCallMethods;
//# sourceMappingURL=toolCall.cjs.map
