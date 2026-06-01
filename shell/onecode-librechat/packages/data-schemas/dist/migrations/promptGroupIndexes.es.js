import logger from '../config/winston.es.js';

/**
 * Old promptGroup indexes that were replaced:
 *   { createdAt: 1, updatedAt: 1 } → { numberOfGenerations: -1, updatedAt: -1, _id: 1 }
 *
 * Mongoose creates new indexes on startup but does NOT drop old ones.
 * This migration removes the superseded index to avoid wasted storage and write overhead.
 */
const SUPERSEDED_PROMPT_GROUP_INDEXES = ['createdAt_1_updatedAt_1'];
async function dropSupersededPromptGroupIndexes(connection) {
    const result = { dropped: [], skipped: [], errors: [] };
    const collectionName = 'promptgroups';
    let collection;
    try {
        collection = connection.db.collection(collectionName);
    }
    catch {
        result.skipped.push(...SUPERSEDED_PROMPT_GROUP_INDEXES.map((idx) => `${collectionName}.${idx} (collection does not exist)`));
        return result;
    }
    let existingIndexes;
    try {
        existingIndexes = await collection.indexes();
    }
    catch {
        result.skipped.push(...SUPERSEDED_PROMPT_GROUP_INDEXES.map((idx) => `${collectionName}.${idx} (could not list indexes)`));
        return result;
    }
    const existingNames = new Set(existingIndexes.map((idx) => idx.name));
    for (const indexName of SUPERSEDED_PROMPT_GROUP_INDEXES) {
        if (!existingNames.has(indexName)) {
            result.skipped.push(`${collectionName}.${indexName}`);
            continue;
        }
        try {
            await collection.dropIndex(indexName);
            result.dropped.push(`${collectionName}.${indexName}`);
            logger.info(`[PromptGroupMigration] Dropped superseded index: ${collectionName}.${indexName}`);
        }
        catch (err) {
            const msg = `${collectionName}.${indexName}: ${err.message}`;
            result.errors.push(msg);
            logger.error(`[PromptGroupMigration] Failed to drop index: ${msg}`);
        }
    }
    return result;
}

export { dropSupersededPromptGroupIndexes };
//# sourceMappingURL=promptGroupIndexes.es.js.map
