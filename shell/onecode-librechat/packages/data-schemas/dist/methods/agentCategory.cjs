'use strict';

var tenantBulkWrite = require('../utils/tenantBulkWrite.cjs');

function createAgentCategoryMethods(mongoose) {
    /**
     * Get all active categories sorted by order
     * @returns Array of active categories
     */
    async function getActiveCategories() {
        const AgentCategory = mongoose.models.AgentCategory;
        return await AgentCategory.find({ isActive: true })
            .sort({ order: 1, label: 1 })
            .lean();
    }
    /**
     * Get categories with agent counts
     * @returns Categories with agent counts
     */
    async function getCategoriesWithCounts() {
        const Agent = mongoose.models.Agent;
        const categoryCounts = await Agent.aggregate([
            { $match: { category: { $exists: true, $ne: null } } },
            { $group: { _id: '$category', count: { $sum: 1 } } },
        ]);
        const countMap = new Map(categoryCounts.map((c) => [c._id, c.count]));
        const categories = await getActiveCategories();
        return categories.map((category) => ({
            ...category,
            agentCount: countMap.get(category.value) || 0,
        }));
    }
    /**
     * Get valid category values for Agent model validation
     * @returns Array of valid category values
     */
    async function getValidCategoryValues() {
        const AgentCategory = mongoose.models.AgentCategory;
        return await AgentCategory.find({ isActive: true }).distinct('value').lean();
    }
    /**
     * Seed initial categories from existing constants
     * @param categories - Array of category data to seed
     * @returns Bulk write result
     */
    async function seedCategories(categories) {
        const AgentCategory = mongoose.models.AgentCategory;
        const operations = categories.map((category, index) => ({
            updateOne: {
                filter: { value: category.value },
                update: {
                    $setOnInsert: {
                        value: category.value,
                        label: category.label || category.value,
                        description: category.description || '',
                        order: category.order || index,
                        isActive: true,
                        custom: category.custom || false,
                    },
                },
                upsert: true,
            },
        }));
        return await tenantBulkWrite.tenantSafeBulkWrite(AgentCategory, operations);
    }
    /**
     * Find a category by value
     * @param value - The category value to search for
     * @returns The category document or null
     */
    async function findCategoryByValue(value) {
        const AgentCategory = mongoose.models.AgentCategory;
        return await AgentCategory.findOne({ value }).lean();
    }
    /**
     * Create a new category
     * @param categoryData - The category data to create
     * @returns The created category
     */
    async function createCategory(categoryData) {
        const AgentCategory = mongoose.models.AgentCategory;
        const category = await AgentCategory.create(categoryData);
        return category.toObject();
    }
    /**
     * Update a category by value
     * @param value - The category value to update
     * @param updateData - The data to update
     * @returns The updated category or null
     */
    async function updateCategory(value, updateData) {
        const AgentCategory = mongoose.models.AgentCategory;
        return await AgentCategory.findOneAndUpdate({ value }, { $set: updateData }, { new: true, runValidators: true }).lean();
    }
    /**
     * Delete a category by value
     * @param value - The category value to delete
     * @returns Whether the deletion was successful
     */
    async function deleteCategory(value) {
        const AgentCategory = mongoose.models.AgentCategory;
        const result = await AgentCategory.deleteOne({ value });
        return result.deletedCount > 0;
    }
    /**
     * Find a category by ID
     * @param id - The category ID to search for
     * @returns The category document or null
     */
    async function findCategoryById(id) {
        const AgentCategory = mongoose.models.AgentCategory;
        return await AgentCategory.findById(id).lean();
    }
    /**
     * Get all categories (active and inactive)
     * @returns Array of all categories
     */
    async function getAllCategories() {
        const AgentCategory = mongoose.models.AgentCategory;
        return await AgentCategory.find({}).sort({ order: 1, label: 1 }).lean();
    }
    /**
     * Ensure default categories exist and update them if they don't have localization keys
     * @returns Promise<boolean> - true if categories were created/updated, false if no changes
     */
    async function ensureDefaultCategories() {
        const AgentCategory = mongoose.models.AgentCategory;
        const defaultCategories = [
            {
                value: 'general',
                label: 'com_agents_category_general',
                description: 'com_agents_category_general_description',
                order: 0,
            },
            {
                value: 'hr',
                label: 'com_agents_category_hr',
                description: 'com_agents_category_hr_description',
                order: 1,
            },
            {
                value: 'rd',
                label: 'com_agents_category_rd',
                description: 'com_agents_category_rd_description',
                order: 2,
            },
            {
                value: 'finance',
                label: 'com_agents_category_finance',
                description: 'com_agents_category_finance_description',
                order: 3,
            },
            {
                value: 'it',
                label: 'com_agents_category_it',
                description: 'com_agents_category_it_description',
                order: 4,
            },
            {
                value: 'sales',
                label: 'com_agents_category_sales',
                description: 'com_agents_category_sales_description',
                order: 5,
            },
            {
                value: 'aftersales',
                label: 'com_agents_category_aftersales',
                description: 'com_agents_category_aftersales_description',
                order: 6,
            },
        ];
        const existingCategories = await getAllCategories();
        const existingCategoryMap = new Map(existingCategories.map((cat) => [cat.value, cat]));
        const updates = [];
        let created = 0;
        for (const defaultCategory of defaultCategories) {
            const existingCategory = existingCategoryMap.get(defaultCategory.value);
            if (existingCategory) {
                const isNotCustom = !existingCategory.custom;
                const needsLocalization = !existingCategory.label.startsWith('com_');
                if (isNotCustom && needsLocalization) {
                    updates.push({
                        value: defaultCategory.value,
                        label: defaultCategory.label,
                        description: defaultCategory.description,
                    });
                }
            }
            else {
                await createCategory({
                    ...defaultCategory,
                    isActive: true,
                    custom: false,
                });
                created++;
            }
        }
        if (updates.length > 0) {
            const bulkOps = updates.map((update) => ({
                updateOne: {
                    filter: { value: update.value, custom: { $ne: true } },
                    update: {
                        $set: {
                            label: update.label,
                            description: update.description,
                        },
                    },
                },
            }));
            await tenantBulkWrite.tenantSafeBulkWrite(AgentCategory, bulkOps, { ordered: false });
        }
        return updates.length > 0 || created > 0;
    }
    return {
        getActiveCategories,
        getCategoriesWithCounts,
        getValidCategoryValues,
        seedCategories,
        findCategoryByValue,
        createCategory,
        updateCategory,
        deleteCategory,
        findCategoryById,
        getAllCategories,
        ensureDefaultCategories,
    };
}

exports.createAgentCategoryMethods = createAgentCategoryMethods;
//# sourceMappingURL=agentCategory.cjs.map
