'use strict';

var mongoose = require('mongoose');

const categoriesSchema = new mongoose.Schema({
    label: {
        type: String,
        required: true,
    },
    value: {
        type: String,
        required: true,
    },
    tenantId: {
        type: String,
        index: true,
    },
});
categoriesSchema.index({ label: 1, tenantId: 1 }, { unique: true });
categoriesSchema.index({ value: 1, tenantId: 1 }, { unique: true });

module.exports = categoriesSchema;
//# sourceMappingURL=categories.cjs.map
