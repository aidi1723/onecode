'use strict';

function createAssistantMethods(mongoose) {
    /**
     * Update an assistant with new data without overwriting existing properties,
     * or create a new assistant if it doesn't exist.
     */
    async function updateAssistantDoc(searchParams, updateData) {
        const Assistant = mongoose.models.Assistant;
        const options = { new: true, upsert: true };
        return await Assistant.findOneAndUpdate(searchParams, updateData, options).lean();
    }
    /**
     * Retrieves an assistant document based on the provided search params.
     */
    async function getAssistant(searchParams) {
        const Assistant = mongoose.models.Assistant;
        return await Assistant.findOne(searchParams).lean();
    }
    /**
     * Retrieves all assistants that match the given search parameters.
     */
    async function getAssistants(searchParams, select = null) {
        const Assistant = mongoose.models.Assistant;
        const query = Assistant.find(searchParams);
        return await (select ? query.select(select) : query).lean();
    }
    /**
     * Deletes an assistant based on the provided search params.
     */
    async function deleteAssistant(searchParams) {
        const Assistant = mongoose.models.Assistant;
        return await Assistant.findOneAndDelete(searchParams);
    }
    /**
     * Deletes all assistants matching the given search parameters.
     */
    async function deleteAssistants(searchParams) {
        const Assistant = mongoose.models.Assistant;
        const result = await Assistant.deleteMany(searchParams);
        return result.deletedCount;
    }
    return {
        updateAssistantDoc,
        deleteAssistant,
        deleteAssistants,
        getAssistants,
        getAssistant,
    };
}

exports.createAssistantMethods = createAssistantMethods;
//# sourceMappingURL=assistant.cjs.map
