'use strict';

var winston = require('../config/winston.cjs');

const options = [
    { label: 'com_ui_idea', value: 'idea' },
    { label: 'com_ui_travel', value: 'travel' },
    { label: 'com_ui_teach_or_explain', value: 'teach_or_explain' },
    { label: 'com_ui_write', value: 'write' },
    { label: 'com_ui_shop', value: 'shop' },
    { label: 'com_ui_code', value: 'code' },
    { label: 'com_ui_misc', value: 'misc' },
    { label: 'com_ui_roleplay', value: 'roleplay' },
    { label: 'com_ui_finance', value: 'finance' },
];
function createCategoriesMethods(_mongoose) {
    /**
     * Retrieves the categories.
     */
    async function getCategories() {
        try {
            return [...options];
        }
        catch (error) {
            winston.error('Error getting categories', error);
            return [];
        }
    }
    return { getCategories };
}

exports.createCategoriesMethods = createCategoriesMethods;
//# sourceMappingURL=categories.cjs.map
