import { PrincipalType } from 'librechat-data-provider';
import { BASE_CONFIG_PRINCIPAL_ID } from '../admin/capabilities.es.js';

function createConfigMethods(mongoose) {
    async function findConfigByPrincipal(principalType, principalId, options, session) {
        const Config = mongoose.models.Config;
        const filter = {
            principalType,
            principalId: principalId.toString(),
        };
        if (!(options === null || options === void 0 ? void 0 : options.includeInactive)) {
            filter.isActive = true;
        }
        return await Config.findOne(filter)
            .session(session !== null && session !== void 0 ? session : null)
            .lean();
    }
    async function listAllConfigs(filter, session) {
        const Config = mongoose.models.Config;
        const where = {};
        if ((filter === null || filter === void 0 ? void 0 : filter.isActive) !== undefined) {
            where.isActive = filter.isActive;
        }
        return await Config.find(where)
            .sort({ priority: 1 })
            .session(session !== null && session !== void 0 ? session : null)
            .lean();
    }
    async function getApplicableConfigs(principals, session) {
        const Config = mongoose.models.Config;
        const basePrincipal = {
            principalType: PrincipalType.ROLE,
            principalId: BASE_CONFIG_PRINCIPAL_ID,
        };
        const principalsQuery = [basePrincipal];
        if (principals && principals.length > 0) {
            for (const p of principals) {
                if (p.principalId !== undefined) {
                    principalsQuery.push({
                        principalType: p.principalType,
                        principalId: p.principalId.toString(),
                    });
                }
            }
        }
        return await Config.find({
            $or: principalsQuery,
            isActive: true,
        })
            .sort({ priority: 1 })
            .session(session !== null && session !== void 0 ? session : null)
            .lean();
    }
    async function upsertConfig(principalType, principalId, principalModel, overrides, priority, session) {
        const Config = mongoose.models.Config;
        const query = {
            principalType,
            principalId: principalId.toString(),
        };
        const update = {
            $set: {
                principalModel,
                overrides,
                priority,
                isActive: true,
            },
            $inc: { configVersion: 1 },
        };
        const options = {
            upsert: true,
            new: true,
            setDefaultsOnInsert: true,
            ...(session ? { session } : {}),
        };
        try {
            return await Config.findOneAndUpdate(query, update, options);
        }
        catch (err) {
            if (err.code === 11000) {
                return await Config.findOneAndUpdate(query, { $set: update.$set, $inc: update.$inc }, { new: true, ...(session ? { session } : {}) });
            }
            throw err;
        }
    }
    async function patchConfigFields(principalType, principalId, principalModel, fields, priority, session) {
        const Config = mongoose.models.Config;
        const setPayload = {
            principalModel,
            priority,
        };
        for (const [path, value] of Object.entries(fields)) {
            setPayload[`overrides.${path}`] = value;
        }
        const options = {
            upsert: true,
            new: true,
            setDefaultsOnInsert: true,
            ...(session ? { session } : {}),
        };
        return await Config.findOneAndUpdate({ principalType, principalId: principalId.toString() }, { $set: setPayload, $inc: { configVersion: 1 } }, options);
    }
    async function unsetConfigField(principalType, principalId, fieldPath, session) {
        const Config = mongoose.models.Config;
        const options = {
            new: true,
            ...(session ? { session } : {}),
        };
        return await Config.findOneAndUpdate({ principalType, principalId: principalId.toString() }, { $unset: { [`overrides.${fieldPath}`]: '' }, $inc: { configVersion: 1 } }, options);
    }
    async function deleteConfig(principalType, principalId, session) {
        const Config = mongoose.models.Config;
        return await Config.findOneAndDelete({
            principalType,
            principalId: principalId.toString(),
        }).session(session !== null && session !== void 0 ? session : null);
    }
    async function toggleConfigActive(principalType, principalId, isActive, session) {
        const Config = mongoose.models.Config;
        return await Config.findOneAndUpdate({ principalType, principalId: principalId.toString() }, { $set: { isActive } }, { new: true, ...(session ? { session } : {}) });
    }
    return {
        listAllConfigs,
        findConfigByPrincipal,
        getApplicableConfigs,
        upsertConfig,
        patchConfigFields,
        unsetConfigField,
        deleteConfig,
        toggleConfigActive,
    };
}

export { createConfigMethods };
//# sourceMappingURL=config.es.js.map
