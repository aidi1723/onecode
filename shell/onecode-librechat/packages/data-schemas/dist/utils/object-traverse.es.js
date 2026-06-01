/**
 * ESM-native object traversal utility
 * Simplified implementation focused on the forEach use case
 */
function isObject(value) {
    if (value === null || typeof value !== 'object') {
        return false;
    }
    // Treat these built-in types as leaf nodes, not objects to traverse
    if (value instanceof Date)
        return false;
    if (value instanceof RegExp)
        return false;
    if (value instanceof Error)
        return false;
    if (value instanceof URL)
        return false;
    // Check for Buffer (Node.js)
    if (typeof Buffer !== 'undefined' && Buffer.isBuffer(value))
        return false;
    // Check for TypedArrays and ArrayBuffer
    if (ArrayBuffer.isView(value))
        return false;
    if (value instanceof ArrayBuffer)
        return false;
    if (value instanceof SharedArrayBuffer)
        return false;
    // Check for other built-in types that shouldn't be traversed
    if (value instanceof Promise)
        return false;
    if (value instanceof WeakMap)
        return false;
    if (value instanceof WeakSet)
        return false;
    if (value instanceof Map)
        return false;
    if (value instanceof Set)
        return false;
    // Check if it's a primitive wrapper object
    const stringTag = Object.prototype.toString.call(value);
    if (stringTag === '[object Boolean]' ||
        stringTag === '[object Number]' ||
        stringTag === '[object String]') {
        return false;
    }
    return true;
}
// Helper to safely set a property on an object or array
function setProperty(obj, key, value) {
    if (Array.isArray(obj) && typeof key === 'number') {
        obj[key] = value;
    }
    else if (!Array.isArray(obj) && typeof key === 'string') {
        obj[key] = value;
    }
    else if (!Array.isArray(obj) && typeof key === 'number') {
        // Handle numeric keys on objects
        obj[key] = value;
    }
}
// Helper to safely delete a property from an object
function deleteProperty(obj, key) {
    if (Array.isArray(obj) && typeof key === 'number') {
        // For arrays, we should use splice, but this is handled in remove()
        // This function is only called for non-array deletion
        return;
    }
    if (!Array.isArray(obj)) {
        delete obj[key];
    }
}
function forEach(obj, callback) {
    const visited = new WeakSet();
    function walk(node, path = [], parent) {
        // Check for circular references
        let circular = null;
        if (isObject(node)) {
            if (visited.has(node)) {
                // Find the circular reference in the parent chain
                let p = parent;
                while (p) {
                    if (p.node === node) {
                        circular = p;
                        break;
                    }
                    p = p.parent;
                }
                return; // Skip circular references
            }
            visited.add(node);
        }
        const key = path.length > 0 ? path[path.length - 1] : undefined;
        const isRoot = path.length === 0;
        const level = path.length;
        // Determine if this is a leaf node
        const isLeaf = !isObject(node) ||
            (Array.isArray(node) && node.length === 0) ||
            Object.keys(node).length === 0;
        // Create context
        const context = {
            node,
            path: [...path],
            parent,
            key,
            isLeaf,
            notLeaf: !isLeaf,
            isRoot,
            notRoot: !isRoot,
            level,
            circular,
            update(value) {
                if (!isRoot && parent && key !== undefined && isObject(parent.node)) {
                    setProperty(parent.node, key, value);
                }
                this.node = value;
            },
            remove() {
                if (!isRoot && parent && key !== undefined && isObject(parent.node)) {
                    if (Array.isArray(parent.node) && typeof key === 'number') {
                        parent.node.splice(key, 1);
                    }
                    else {
                        deleteProperty(parent.node, key);
                    }
                }
            },
        };
        // Call the callback with the context
        callback.call(context, node);
        // Traverse children if not circular and is an object
        if (!circular && isObject(node) && !isLeaf) {
            if (Array.isArray(node)) {
                for (let i = 0; i < node.length; i++) {
                    walk(node[i], [...path, i], context);
                }
            }
            else {
                for (const [childKey, childValue] of Object.entries(node)) {
                    walk(childValue, [...path, childKey], context);
                }
            }
        }
    }
    walk(obj);
}
// Main traverse function that returns an object with forEach method
function traverse(obj) {
    return {
        forEach(callback) {
            forEach(obj, callback);
        },
    };
}

export { traverse as default };
//# sourceMappingURL=object-traverse.es.js.map
