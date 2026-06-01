import file from '../schema/file.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createFileModel(mongoose) {
    applyTenantIsolation(file);
    return mongoose.models.File || mongoose.model('File', file);
}

export { createFileModel };
//# sourceMappingURL=file.es.js.map
