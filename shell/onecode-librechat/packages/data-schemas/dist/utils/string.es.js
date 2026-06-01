/**
 * Escapes special regex characters in a string.
 */
function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export { escapeRegExp };
//# sourceMappingURL=string.es.js.map
