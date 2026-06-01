'use strict';

/**
 * Escapes special regex characters in a string.
 */
function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

exports.escapeRegExp = escapeRegExp;
//# sourceMappingURL=string.cjs.map
