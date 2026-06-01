import MemoryEntrySchema from '../schema/memory.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createMemoryModel(mongoose) {
    applyTenantIsolation(MemoryEntrySchema);
    return mongoose.models.MemoryEntry || mongoose.model('MemoryEntry', MemoryEntrySchema);
}

export { createMemoryModel };
//# sourceMappingURL=memory.es.js.map
