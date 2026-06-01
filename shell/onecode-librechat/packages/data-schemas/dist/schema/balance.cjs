'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');

const balanceSchema = new mongoose.Schema({
    user: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        index: true,
        required: true,
    },
    // 1000 tokenCredits = 1 mill ($0.001 USD)
    tokenCredits: {
        type: Number,
        default: 0,
    },
    // Automatic refill settings
    autoRefillEnabled: {
        type: Boolean,
        default: false,
    },
    refillIntervalValue: {
        type: Number,
        default: 30,
    },
    refillIntervalUnit: {
        type: String,
        enum: librechatDataProvider.REFILL_INTERVAL_UNITS,
        default: 'days',
    },
    lastRefill: {
        type: Date,
        default: Date.now,
    },
    // amount to add on each refill
    refillAmount: {
        type: Number,
        default: 0,
    },
    tenantId: {
        type: String,
        index: true,
    },
});

module.exports = balanceSchema;
//# sourceMappingURL=balance.cjs.map
