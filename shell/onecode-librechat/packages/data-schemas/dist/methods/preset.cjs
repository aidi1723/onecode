'use strict';

var winston = require('../config/winston.cjs');

function createPresetMethods(mongoose) {
    /**
     * Retrieves a single preset by user and presetId.
     */
    async function getPreset(user, presetId) {
        try {
            const Preset = mongoose.models.Preset;
            return await Preset.findOne({ user, presetId }).lean();
        }
        catch (error) {
            winston.error('[getPreset] Error getting single preset', error);
            return { message: 'Error getting single preset' };
        }
    }
    /**
     * Retrieves all presets for a user, sorted by order then updatedAt.
     */
    async function getPresets(user, filter = {}) {
        try {
            const Preset = mongoose.models.Preset;
            const presets = await Preset.find({ ...filter, user }).lean();
            const defaultValue = 10000;
            presets.sort((a, b) => {
                var _a, _b;
                const orderA = a.order !== undefined ? a.order : defaultValue;
                const orderB = b.order !== undefined ? b.order : defaultValue;
                if (orderA !== orderB) {
                    return orderA - orderB;
                }
                return new Date((_a = b.updatedAt) !== null && _a !== void 0 ? _a : 0).getTime() - new Date((_b = a.updatedAt) !== null && _b !== void 0 ? _b : 0).getTime();
            });
            return presets;
        }
        catch (error) {
            winston.error('[getPresets] Error getting presets', error);
            return { message: 'Error retrieving presets' };
        }
    }
    /**
     * Saves a preset. Handles default preset logic and tool normalization.
     */
    async function savePreset(user, { presetId, newPresetId, defaultPreset, ...preset }) {
        var _a;
        try {
            const Preset = mongoose.models.Preset;
            const setter = { $set: {} };
            const { user: _unusedUser, ...cleanPreset } = preset;
            const update = { presetId, ...cleanPreset };
            if (preset.tools && Array.isArray(preset.tools)) {
                update.tools =
                    (_a = preset.tools
                        .map((tool) => (typeof tool === 'object' && (tool === null || tool === void 0 ? void 0 : tool.pluginKey) ? tool.pluginKey : tool))
                        .filter((toolName) => typeof toolName === 'string')) !== null && _a !== void 0 ? _a : [];
            }
            if (newPresetId) {
                update.presetId = newPresetId;
            }
            if (defaultPreset) {
                update.defaultPreset = defaultPreset;
                update.order = 0;
                const currentDefault = await Preset.findOne({ defaultPreset: true, user });
                if (currentDefault && currentDefault.presetId !== presetId) {
                    await Preset.findByIdAndUpdate(currentDefault._id, {
                        $unset: { defaultPreset: '', order: '' },
                    });
                }
            }
            else if (defaultPreset === false) {
                update.defaultPreset = undefined;
                update.order = undefined;
                setter['$unset'] = { defaultPreset: '', order: '' };
            }
            setter.$set = update;
            return await Preset.findOneAndUpdate({ presetId, user }, setter, {
                new: true,
                upsert: true,
            });
        }
        catch (error) {
            winston.error('[savePreset] Error saving preset', error);
            return { message: 'Error saving preset' };
        }
    }
    /**
     * Deletes presets matching the given filter for a user.
     */
    async function deletePresets(user, filter = {}) {
        const Preset = mongoose.models.Preset;
        const deleteCount = await Preset.deleteMany({ ...filter, user });
        return deleteCount;
    }
    return {
        getPreset,
        getPresets,
        savePreset,
        deletePresets,
    };
}

exports.createPresetMethods = createPresetMethods;
//# sourceMappingURL=preset.cjs.map
