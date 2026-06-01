import 'librechat-data-provider';

/**
 * Common role combinations
 */
var RoleBits;
(function (RoleBits) {
    /** 0001 = 1 */
    RoleBits[RoleBits["VIEWER"] = 1] = "VIEWER";
    /** 0011 = 3 */
    RoleBits[RoleBits["EDITOR"] = 3] = "EDITOR";
    /** 0111 = 7 */
    RoleBits[RoleBits["MANAGER"] = 7] = "MANAGER";
    /** 1111 = 15 */
    RoleBits[RoleBits["OWNER"] = 15] = "OWNER";
})(RoleBits || (RoleBits = {}));

export { RoleBits };
//# sourceMappingURL=enum.es.js.map
