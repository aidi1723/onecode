'use strict';

var _ = require('lodash');
var librechatDataProvider = require('librechat-data-provider');
var meilisearch = require('meilisearch');
var meiliLogger = require('../../config/meiliLogger.cjs');
var retention = require('../../utils/retention.cjs');

// Environment flags
/**
 * Flag to indicate if search is enabled based on environment variables.
 */
const searchEnabled = process.env.SEARCH != null && process.env.SEARCH.toLowerCase() === 'true';
/**
 * Flag to indicate if MeiliSearch is enabled based on required environment variables.
 */
const meiliEnabled = process.env.MEILI_HOST != null && process.env.MEILI_MASTER_KEY != null && searchEnabled;
/**
 * Get sync configuration from environment variables
 */
const getSyncConfig = () => ({
    batchSize: parseInt(process.env.MEILI_SYNC_BATCH_SIZE || '100', 10),
    delayMs: parseInt(process.env.MEILI_SYNC_DELAY_MS || '100', 10),
});
const hasSchemaPath = (schema, path) => Object.prototype.hasOwnProperty.call(schema.obj, path);
const explicitTemporaryFlagKey = 'meiliExplicitTemporaryFlag';
const buildIndexableQuery = (schema) => {
    if (!hasSchemaPath(schema, 'isTemporary')) {
        return hasSchemaPath(schema, 'expiredAt') ? retention.legacyPermanentExpirationFilter() : {};
    }
    return retention.buildRetentionVisibilityFilter();
};
const hasActiveExpiration = (expiredAt) => _.isNil(expiredAt) || new Date(expiredAt).getTime() > Date.now();
/**
 * `isTemporary` defaults to `false` on the schema, so hydrated legacy documents
 * can appear non-temporary even when the field is absent from MongoDB. `$isDefault`
 * lets us distinguish that schema default from an explicit stored flag, and
 * `$locals` carries the pre-save answer into post hooks after Mongoose mutates
 * document state.
 */
const hasExplicitTemporaryFlag = (doc) => {
    var _a;
    return typeof ((_a = doc.$locals) === null || _a === void 0 ? void 0 : _a[explicitTemporaryFlagKey]) === 'boolean'
        ? doc.$locals[explicitTemporaryFlagKey]
        : doc.isTemporary != null && !doc.$isDefault('isTemporary');
};
const captureExplicitTemporaryFlag = (doc) => {
    doc.$locals[explicitTemporaryFlagKey] = doc.isTemporary != null && !doc.$isDefault('isTemporary');
};
/**
 * Index only retained non-temporary records whose flag was explicitly stored,
 * plus legacy permanent records that have no retention deadline. Legacy records
 * with an expiration are treated as temporary and stay out of search.
 */
const isIndexableDocument = (doc) => (doc.isTemporary === false &&
    hasExplicitTemporaryFlag(doc) &&
    hasActiveExpiration(doc.expiredAt)) ||
    (!hasExplicitTemporaryFlag(doc) && _.isNil(doc.expiredAt));
/**
 * Validates the required options for configuring the mongoMeili plugin.
 */
const validateOptions = (options) => {
    const requiredKeys = ['host', 'apiKey', 'indexName', 'primaryKey'];
    requiredKeys.forEach((key) => {
        if (!options[key]) {
            throw new Error(`Missing mongoMeili Option: ${key}`);
        }
    });
};
/**
 * Helper function to process documents in batches with rate limiting
 */
const processBatch = async (items, batchSize, delayMs, processor) => {
    for (let i = 0; i < items.length; i += batchSize) {
        const batch = items.slice(i, i + batchSize);
        await processor(batch);
        // Add delay between batches to prevent overwhelming resources
        if (i + batchSize < items.length && delayMs > 0) {
            await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
    }
};
/**
 * Factory function to create a MeiliMongooseModel class which extends a Mongoose model.
 * This class contains static and instance methods to synchronize and manage the MeiliSearch index
 * corresponding to the MongoDB collection.
 *
 * @param config - Configuration object.
 * @param config.index - The MeiliSearch index object.
 * @param config.attributesToIndex - List of attributes to index.
 * @param config.primaryKey - The primary key field for MeiliSearch document operations.
 * @param config.syncOptions - Sync configuration options.
 * @returns A class definition that will be loaded into the Mongoose schema.
 */
const createMeiliMongooseModel = ({ index, getIndexableQuery, attributesToIndex, primaryKey, syncOptions, }) => {
    const syncConfig = { ...getSyncConfig(), ...syncOptions };
    class MeiliMongooseModel {
        /**
         * Get the current sync progress
         */
        static async getSyncProgress() {
            const indexableQuery = getIndexableQuery();
            const totalDocuments = await this.countDocuments(indexableQuery);
            const indexedDocuments = await this.countDocuments({
                ...indexableQuery,
                _meiliIndex: true,
            });
            return {
                totalProcessed: indexedDocuments,
                totalDocuments,
                isComplete: indexedDocuments === totalDocuments,
            };
        }
        /**
         * Synchronizes data between the MongoDB collection and the MeiliSearch index by
         * incrementally indexing only non-temporary documents where `_meiliIndex` is not `true`.
         * */
        static async syncWithMeili() {
            const startTime = Date.now();
            const { batchSize, delayMs } = syncConfig;
            const collectionName = primaryKey === 'messageId' ? 'messages' : 'conversations';
            meiliLogger.info(`[syncWithMeili] Starting sync for ${collectionName} with batch size ${batchSize}`);
            // Get approximate total count for raw estimation, the sync should not overcome this number
            const approxTotalCount = await this.estimatedDocumentCount();
            meiliLogger.info(`[syncWithMeili] Approximate total number of all ${collectionName}: ${approxTotalCount}`);
            try {
                // First, handle documents that need to be removed from Meili
                meiliLogger.info(`[syncWithMeili] Starting cleanup of Meili index ${index.uid} before sync`);
                await this.cleanupMeiliIndex(index, primaryKey, batchSize, delayMs);
                meiliLogger.info(`[syncWithMeili] Completed cleanup of Meili index: ${index.uid}`);
            }
            catch (error) {
                meiliLogger.error('[syncWithMeili] Error during cleanup Meili before sync:', error);
                throw error;
            }
            let processedCount = 0;
            let hasMore = true;
            while (hasMore) {
                const indexableQuery = getIndexableQuery();
                const query = {
                    ...indexableQuery,
                    _meiliIndex: { $ne: true },
                };
                try {
                    const documents = await this.find(query)
                        .select(attributesToIndex.join(' ') + ' _meiliIndex')
                        .limit(batchSize)
                        .lean();
                    // Check if there are more documents to process
                    if (documents.length === 0) {
                        meiliLogger.info('[syncWithMeili] No more documents to process');
                        break;
                    }
                    // Process the batch
                    await this.processSyncBatch(index, documents);
                    processedCount += documents.length;
                    meiliLogger.info(`[syncWithMeili] Processed: ${processedCount}`);
                    if (documents.length < batchSize) {
                        hasMore = false;
                    }
                    // Add delay to prevent overwhelming resources
                    if (hasMore && delayMs > 0) {
                        await new Promise((resolve) => setTimeout(resolve, delayMs));
                    }
                }
                catch (error) {
                    meiliLogger.error('[syncWithMeili] Error processing documents batch:', error);
                    throw error;
                }
            }
            const duration = Date.now() - startTime;
            meiliLogger.info(`[syncWithMeili] Completed sync for ${collectionName}. Processed ${processedCount} documents in ${duration}ms`);
        }
        /**
         * Process a batch of documents for syncing
         */
        static async processSyncBatch(index, documents) {
            if (documents.length === 0) {
                return;
            }
            // Format documents for MeiliSearch
            const formattedDocs = documents.map((doc) => _.omitBy(_.pick(doc, attributesToIndex), (_v, k) => k.startsWith('$')));
            try {
                // Add documents to MeiliSearch
                await index.addDocumentsInBatches(formattedDocs, undefined, { primaryKey });
                // Update MongoDB to mark documents as indexed.
                // { timestamps: false } prevents Mongoose from touching updatedAt, preserving
                // original conversation/message timestamps (fixes sidebar chronological sort).
                const docsIds = documents.map((doc) => doc._id);
                await this.updateMany({ _id: { $in: docsIds } }, { $set: { _meiliIndex: true } }, { timestamps: false });
            }
            catch (error) {
                meiliLogger.error('[processSyncBatch] Error processing batch:', error);
                throw error;
            }
        }
        /**
         * Clean up documents in MeiliSearch that no longer exist in MongoDB
         */
        static async cleanupMeiliIndex(index, primaryKey, batchSize, delayMs) {
            try {
                let offset = 0;
                let moreDocuments = true;
                while (moreDocuments) {
                    const batch = await index.getDocuments({ limit: batchSize, offset });
                    if (batch.results.length === 0) {
                        moreDocuments = false;
                        break;
                    }
                    const meiliIds = batch.results.map((doc) => doc[primaryKey]);
                    const query = {};
                    query[primaryKey] = { $in: meiliIds };
                    const existingDocs = await this.find({ ...query, ...getIndexableQuery() })
                        .select(primaryKey)
                        .lean();
                    const existingIds = new Set(existingDocs.map((doc) => doc[primaryKey]));
                    // Delete documents that don't exist in MongoDB
                    const toDelete = meiliIds.filter((id) => !existingIds.has(id));
                    if (toDelete.length > 0) {
                        await index.deleteDocuments(toDelete.map(String));
                        meiliLogger.debug(`[cleanupMeiliIndex] Deleted ${toDelete.length} orphaned documents`);
                    }
                    // if fetch documents request returns less documents than limit, all documents are processed
                    if (batch.results.length < batchSize) {
                        break;
                    }
                    offset += batchSize - toDelete.length;
                    // Add delay between batches
                    if (delayMs > 0) {
                        await new Promise((resolve) => setTimeout(resolve, delayMs));
                    }
                }
            }
            catch (error) {
                meiliLogger.error('[cleanupMeiliIndex] Error during cleanup:', error);
            }
        }
        /**
         * Updates settings for the MeiliSearch index
         */
        static async setMeiliIndexSettings(settings) {
            return await index.updateSettings(settings);
        }
        /**
         * Searches the MeiliSearch index and optionally populates results
         */
        static async meiliSearch(q, params, populate) {
            const data = await index.search(q, params);
            if (populate) {
                const query = {};
                query[primaryKey] = _.map(data.hits, (hit) => hit[primaryKey]);
                const projection = Object.keys(this.schema.obj).reduce((results, key) => {
                    if (!key.startsWith('$')) {
                        results[key] = 1;
                    }
                    return results;
                }, { _id: 1, __v: 1 });
                const hitsFromMongoose = await this.find(query, projection).lean();
                const populatedHits = data.hits.map((hit) => {
                    hit[primaryKey];
                    const originalHit = _.find(hitsFromMongoose, (item) => {
                        const typedItem = item;
                        return typedItem[primaryKey] === hit[primaryKey];
                    });
                    return {
                        ...(originalHit && typeof originalHit === 'object' ? originalHit : {}),
                        ...hit,
                    };
                });
                data.hits = populatedHits;
            }
            return data;
        }
        /**
         * Preprocesses the current document for indexing
         */
        preprocessObjectForIndex() {
            const object = _.omitBy(_.pick(this.toJSON(), attributesToIndex), (v, k) => k.startsWith('$'));
            if (object.conversationId &&
                typeof object.conversationId === 'string' &&
                object.conversationId.includes('|')) {
                object.conversationId = object.conversationId.replace(/\|/g, '--');
            }
            if (object.content && Array.isArray(object.content)) {
                object.text = librechatDataProvider.parseTextParts(object.content);
                delete object.content;
            }
            return object;
        }
        /**
         * Adds the current document to the MeiliSearch index with retry logic
         */
        async addObjectToMeili(next) {
            if (!isIndexableDocument(this)) {
                return next();
            }
            const object = this.preprocessObjectForIndex();
            const maxRetries = 3;
            let retryCount = 0;
            while (retryCount < maxRetries) {
                try {
                    await index.addDocuments([object], { primaryKey });
                    break;
                }
                catch (error) {
                    retryCount++;
                    if (retryCount >= maxRetries) {
                        meiliLogger.error('[addObjectToMeili] Error adding document to Meili after retries:', error);
                        return next();
                    }
                    // Exponential backoff
                    await new Promise((resolve) => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
                }
            }
            try {
                // eslint-disable-next-line no-restricted-syntax -- _meiliIndex is an internal bookkeeping flag, not tenant-scoped data
                await this.collection.updateOne({ _id: this._id }, { $set: { _meiliIndex: true } });
            }
            catch (error) {
                meiliLogger.error('[addObjectToMeili] Error updating _meiliIndex field:', error);
                return next();
            }
            next();
        }
        /**
         * Updates the current document in the MeiliSearch index
         */
        async updateObjectToMeili(next) {
            try {
                if (!isIndexableDocument(this)) {
                    await index.deleteDocument(String(this[primaryKey]));
                    const model = this.constructor;
                    await model.updateOne({ _id: this._id }, { $set: { _meiliIndex: false } });
                    return next();
                }
                const object = this.preprocessObjectForIndex();
                await index.updateDocuments([object], { primaryKey });
                next();
            }
            catch (error) {
                meiliLogger.error('[updateObjectToMeili] Error updating document in Meili:', error);
                return next();
            }
        }
        /**
         * Deletes the current document from the MeiliSearch index.
         *
         * @returns {Promise<void>}
         */
        async deleteObjectFromMeili(next) {
            try {
                await index.deleteDocument(String(this[primaryKey]));
                next();
            }
            catch (error) {
                meiliLogger.error('[deleteObjectFromMeili] Error deleting document from Meili:', error);
                return next();
            }
        }
        /**
         * Post-save hook to synchronize the document with MeiliSearch.
         *
         * If the document is already indexed (i.e. `_meiliIndex` is true), it updates it;
         * otherwise, it adds the document to the index.
         */
        postSaveHook(next) {
            if (this._meiliIndex) {
                this.updateObjectToMeili(next);
            }
            else {
                this.addObjectToMeili(next);
            }
        }
        /**
         * Post-update hook to update the document in MeiliSearch.
         *
         * This hook is triggered after a document update, ensuring that changes are
         * propagated to the MeiliSearch index if the document is indexed.
         */
        postUpdateHook(next) {
            if (this._meiliIndex) {
                this.updateObjectToMeili(next);
            }
            else {
                next();
            }
        }
        /**
         * Post-remove hook to delete the document from MeiliSearch.
         *
         * This hook is triggered after a document is removed, ensuring that the document
         * is also removed from the MeiliSearch index if it was previously indexed.
         */
        postRemoveHook(next) {
            if (this._meiliIndex) {
                this.deleteObjectFromMeili(next);
            }
            else {
                next();
            }
        }
    }
    return MeiliMongooseModel;
};
/**
 * Mongoose plugin to synchronize MongoDB collections with a MeiliSearch index.
 *
 * This plugin:
 *   - Validates the provided options.
 *   - Adds a `_meiliIndex` field to the schema to track indexing status.
 *   - Sets up a MeiliSearch client and creates an index if it doesn't already exist.
 *   - Loads class methods for syncing, searching, and managing documents in MeiliSearch.
 *   - Registers Mongoose hooks (post-save, post-update, post-remove, etc.) to maintain index consistency.
 *
 * @param schema - The Mongoose schema to which the plugin is applied.
 * @param options - Configuration options.
 * @param options.host - The MeiliSearch host.
 * @param options.apiKey - The MeiliSearch API key.
 * @param options.indexName - The name of the MeiliSearch index.
 * @param options.primaryKey - The primary key field for indexing.
 * @param options.syncBatchSize - Batch size for sync operations.
 * @param options.syncDelayMs - Delay between batches in milliseconds.
 */
function mongoMeili(schema, options) {
    const mongoose = options.mongoose;
    validateOptions(options);
    // Add _meiliIndex field to the schema to track if a document has been indexed in MeiliSearch.
    schema.add({
        _meiliIndex: {
            type: Boolean,
            required: false,
            select: false,
            default: false,
        },
    });
    const { host, apiKey, indexName, primaryKey } = options;
    const syncOptions = {
        batchSize: options.syncBatchSize || getSyncConfig().batchSize,
        delayMs: options.syncDelayMs || getSyncConfig().delayMs,
    };
    const client = new meilisearch.MeiliSearch({ host, apiKey });
    /** Create index only if it doesn't exist */
    const index = client.index(indexName);
    (async () => {
        try {
            await index.getRawInfo();
            meiliLogger.debug(`[mongoMeili] Index ${indexName} already exists`);
        }
        catch (error) {
            const errorCode = error === null || error === void 0 ? void 0 : error.code;
            if (errorCode === 'index_not_found') {
                try {
                    meiliLogger.info(`[mongoMeili] Creating new index: ${indexName}`);
                    const enqueued = await client.createIndex(indexName, { primaryKey });
                    const task = await client.waitForTask(enqueued.taskUid, {
                        timeOutMs: 10000,
                        intervalMs: 100,
                    });
                    meiliLogger.debug(`[mongoMeili] Index ${indexName} creation task:`, task);
                    if (task.status !== 'succeeded') {
                        const taskError = task.error;
                        if ((taskError === null || taskError === void 0 ? void 0 : taskError.code) === 'index_already_exists') {
                            meiliLogger.debug(`[mongoMeili] Index ${indexName} was created by another instance`);
                        }
                        else {
                            meiliLogger.warn(`[mongoMeili] Index ${indexName} creation failed:`, taskError);
                        }
                    }
                    else {
                        meiliLogger.info(`[mongoMeili] Successfully created index: ${indexName}`);
                    }
                }
                catch (createError) {
                    if (createError instanceof meilisearch.MeiliSearchTimeOutError) {
                        meiliLogger.warn(`[mongoMeili] Timed out waiting for index ${indexName} creation`);
                    }
                    else {
                        meiliLogger.warn(`[mongoMeili] Error creating index ${indexName}:`, createError);
                    }
                }
            }
            else {
                meiliLogger.error(`[mongoMeili] Error checking index ${indexName}:`, error);
            }
        }
        try {
            await index.updateSettings({
                filterableAttributes: ['user'],
            });
            meiliLogger.debug(`[mongoMeili] Updated index ${indexName} settings to make 'user' filterable`);
        }
        catch (settingsError) {
            meiliLogger.error(`[mongoMeili] Error updating index settings for ${indexName}:`, settingsError);
        }
    })();
    // Collect attributes from the schema that should be indexed
    const attributesToIndex = [
        ...Object.entries(schema.obj).reduce((results, [key, value]) => {
            const schemaValue = value;
            return schemaValue.meiliIndex ? [...results, key] : results;
        }, []),
    ];
    // CRITICAL: Always include 'user' field for proper filtering
    // This ensures existing deployments can filter by user after migration
    if (schema.obj.user && !attributesToIndex.includes('user')) {
        attributesToIndex.push('user');
        meiliLogger.debug(`[mongoMeili] Added 'user' field to ${indexName} index attributes`);
    }
    schema.loadClass(createMeiliMongooseModel({
        index,
        getIndexableQuery: () => buildIndexableQuery(schema),
        attributesToIndex,
        primaryKey,
        syncOptions,
    }));
    // Register Mongoose hooks
    schema.pre('save', function (next) {
        if (hasSchemaPath(schema, 'isTemporary')) {
            captureExplicitTemporaryFlag(this);
        }
        next();
    });
    schema.post('save', function (doc, next) {
        var _a;
        (_a = doc.postSaveHook) === null || _a === void 0 ? void 0 : _a.call(doc, next);
    });
    schema.post('updateOne', function (doc, next) {
        var _a;
        (_a = doc.postUpdateHook) === null || _a === void 0 ? void 0 : _a.call(doc, next);
    });
    schema.post('deleteOne', function (doc, next) {
        var _a;
        (_a = doc.postRemoveHook) === null || _a === void 0 ? void 0 : _a.call(doc, next);
    });
    // Pre-deleteMany hook: remove corresponding documents from MeiliSearch when multiple documents are deleted.
    schema.pre('deleteMany', async function (next) {
        if (!meiliEnabled) {
            return next();
        }
        try {
            const conditions = this.getQuery();
            const { batchSize, delayMs } = syncOptions;
            if (Object.prototype.hasOwnProperty.call(schema.obj, 'messages')) {
                const convoIndex = client.index('convos');
                const deletedConvos = await mongoose
                    .model('Conversation')
                    .find(conditions)
                    .select('conversationId')
                    .lean();
                // Process deletions in batches
                await processBatch(deletedConvos, batchSize, delayMs, async (batch) => {
                    const promises = batch.map((convo) => convoIndex.deleteDocument(convo.conversationId));
                    await Promise.all(promises);
                });
            }
            if (Object.prototype.hasOwnProperty.call(schema.obj, 'messageId')) {
                const messageIndex = client.index('messages');
                const deletedMessages = await mongoose
                    .model('Message')
                    .find(conditions)
                    .select('messageId')
                    .lean();
                // Process deletions in batches
                await processBatch(deletedMessages, batchSize, delayMs, async (batch) => {
                    const promises = batch.map((message) => messageIndex.deleteDocument(message.messageId));
                    await Promise.all(promises);
                });
            }
            return next();
        }
        catch (error) {
            if (meiliEnabled) {
                meiliLogger.error('[MeiliMongooseModel.deleteMany] There was an issue deleting conversation indexes upon deletion. Next startup may trigger syncing.', error);
            }
            return next();
        }
    });
    // Post-findOneAndUpdate hook
    schema.post('findOneAndUpdate', async function (doc, next) {
        var _a;
        if (!meiliEnabled) {
            return next();
        }
        if (doc.unfinished) {
            return next();
        }
        let meiliDoc;
        if (doc.messages) {
            try {
                meiliDoc = await client.index('convos').getDocument(doc.conversationId);
            }
            catch (error) {
                meiliLogger.debug('[MeiliMongooseModel.findOneAndUpdate] Convo not found in MeiliSearch and will index ' +
                    doc.conversationId, error);
            }
        }
        if (meiliDoc && meiliDoc.title === doc.title) {
            return next();
        }
        (_a = doc.postSaveHook) === null || _a === void 0 ? void 0 : _a.call(doc, next);
    });
}

module.exports = mongoMeili;
//# sourceMappingURL=mongoMeili.cjs.map
