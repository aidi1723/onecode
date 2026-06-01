/** Returns true when `id` is a 24-character hex string (MongoDB ObjectId format). */
const isValidObjectIdString = (id) => /^[a-f\d]{24}$/i.test(id);

export { isValidObjectIdString };
//# sourceMappingURL=objectId.es.js.map
