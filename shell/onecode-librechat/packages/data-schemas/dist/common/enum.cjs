'use strict';

require('librechat-data-provider');

/**
 * Common role combinations
 */
exports.RoleBits = void 0;
(function (RoleBits) {
    /** 0001 = 1 */
    RoleBits[RoleBits["VIEWER"] = 1] = "VIEWER";
    /** 0011 = 3 */
    RoleBits[RoleBits["EDITOR"] = 3] = "EDITOR";
    /** 0111 = 7 */
    RoleBits[RoleBits["MANAGER"] = 7] = "MANAGER";
    /** 1111 = 15 */
    RoleBits[RoleBits["OWNER"] = 15] = "OWNER";
})(exports.RoleBits || (exports.RoleBits = {}));
//# sourceMappingURL=enum.cjs.map
