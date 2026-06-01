import { ErrorTypes } from 'librechat-data-provider';
import { encrypt, decrypt } from '../crypto/index.es.js';
import logger from '../config/winston.es.js';

/** Factory function that takes mongoose instance and returns the key methods */
function createKeyMethods(mongoose) {
    /**
     * Retrieves and decrypts the key value for a given user identified by userId and identifier name.
     * @param params - The parameters object
     * @param params.userId - The unique identifier for the user
     * @param params.name - The name associated with the key
     * @returns The decrypted key value
     * @throws Error if the key is not found or if there is a problem during key retrieval
     * @description This function searches for a user's key in the database using their userId and name.
     *              If found, it decrypts the value of the key and returns it. If no key is found, it throws
     *              an error indicating that there is no user key available.
     */
    async function getUserKey(params) {
        const { userId, name } = params;
        const Key = mongoose.models.Key;
        const keyValue = (await Key.findOne({ userId, name }).lean());
        if (!keyValue) {
            throw new Error(JSON.stringify({
                type: ErrorTypes.NO_USER_KEY,
            }));
        }
        return await decrypt(keyValue.value);
    }
    /**
     * Retrieves, decrypts, and parses the key values for a given user identified by userId and name.
     * @param params - The parameters object
     * @param params.userId - The unique identifier for the user
     * @param params.name - The name associated with the key
     * @returns The decrypted and parsed key values
     * @throws Error if the key is invalid or if there is a problem during key value parsing
     * @description This function retrieves a user's encrypted key using their userId and name, decrypts it,
     *              and then attempts to parse the decrypted string into a JSON object. If the parsing fails,
     *              it throws an error indicating that the user key is invalid.
     */
    async function getUserKeyValues(params) {
        const { userId, name } = params;
        const userValues = await getUserKey({ userId, name });
        try {
            return JSON.parse(userValues);
        }
        catch (e) {
            logger.error('[getUserKeyValues]', e);
            throw new Error(JSON.stringify({
                type: ErrorTypes.INVALID_USER_KEY,
            }));
        }
    }
    /**
     * Retrieves the expiry information of a user's key identified by userId and name.
     * @param params - The parameters object
     * @param params.userId - The unique identifier for the user
     * @param params.name - The name associated with the key
     * @returns The expiry date of the key or null if the key doesn't exist
     * @description This function fetches a user's key from the database using their userId and name and
     *              returns its expiry date. If the key is not found, it returns null for the expiry date.
     */
    async function getUserKeyExpiry(params) {
        const { userId, name } = params;
        const Key = mongoose.models.Key;
        const keyValue = (await Key.findOne({ userId, name }).lean());
        if (!keyValue) {
            return { expiresAt: null };
        }
        return { expiresAt: keyValue.expiresAt || 'never' };
    }
    /**
     * Updates or inserts a new key for a given user identified by userId and name, with a specified value and expiry date.
     * @param params - The parameters object
     * @param params.userId - The unique identifier for the user
     * @param params.name - The name associated with the key
     * @param params.value - The value to be encrypted and stored as the key's value
     * @param params.expiresAt - The expiry date for the key [optional]
     * @returns The updated or newly inserted key document
     * @description This function either updates an existing user key or inserts a new one into the database,
     *              after encrypting the provided value. It sets the provided expiry date for the key (or unsets for no expiry).
     */
    async function updateUserKey(params) {
        const { userId, name, value, expiresAt = null } = params;
        const Key = mongoose.models.Key;
        const encryptedValue = await encrypt(value);
        const updateObject = {
            userId,
            name,
            value: encryptedValue,
        };
        const updateQuery = {
            $set: updateObject,
        };
        if (expiresAt) {
            updateObject.expiresAt = new Date(expiresAt);
        }
        else {
            updateQuery.$unset = { expiresAt: '' };
        }
        return await Key.findOneAndUpdate({ userId, name }, updateQuery, {
            upsert: true,
            new: true,
        }).lean();
    }
    /**
     * Deletes a key or all keys for a given user identified by userId, optionally based on a specified name.
     * @param params - The parameters object
     * @param params.userId - The unique identifier for the user
     * @param params.name - The name associated with the key to delete. If not provided and all is true, deletes all keys
     * @param params.all - Whether to delete all keys for the user
     * @returns The result of the deletion operation
     * @description This function deletes a specific key or all keys for a user from the database.
     *              If a name is provided and all is false, it deletes only the key with that name.
     *              If all is true, it ignores the name and deletes all keys for the user.
     */
    async function deleteUserKey(params) {
        const { userId, name, all = false } = params;
        const Key = mongoose.models.Key;
        if (all) {
            return await Key.deleteMany({ userId });
        }
        return await Key.findOneAndDelete({ userId, name }).lean();
    }
    return {
        getUserKey,
        updateUserKey,
        deleteUserKey,
        getUserKeyValues,
        getUserKeyExpiry,
    };
}

export { createKeyMethods };
//# sourceMappingURL=key.es.js.map
