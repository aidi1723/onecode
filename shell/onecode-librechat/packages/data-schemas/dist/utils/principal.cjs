'use strict';

var mongoose = require('mongoose');
var librechatDataProvider = require('librechat-data-provider');

/**
 * Normalizes a principalId to the correct type for MongoDB queries and storage.
 * USER and GROUP principals are stored as ObjectIds; ROLE principals are strings.
 * Ensures a string caller ID is cast to ObjectId so it matches documents written
 * by `grantCapability` — which always stores user/group IDs as ObjectIds to match
 * what `getUserPrincipals` returns.
 */
const normalizePrincipalId = (principalId, principalType) => {
    if (typeof principalId === 'string' && principalType !== librechatDataProvider.PrincipalType.ROLE) {
        if (!mongoose.Types.ObjectId.isValid(principalId)) {
            throw new TypeError(`Invalid ObjectId string for ${principalType}: "${principalId}"`);
        }
        return new mongoose.Types.ObjectId(principalId);
    }
    return principalId;
};

exports.normalizePrincipalId = normalizePrincipalId;
//# sourceMappingURL=principal.cjs.map
