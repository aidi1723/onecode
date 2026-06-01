import userSchema from '../schema/user.es.js';
import { applyTenantIsolation } from './plugins/tenantIsolation.es.js';

function createUserModel(mongoose) {
    applyTenantIsolation(userSchema);
    return mongoose.models.User || mongoose.model('User', userSchema);
}

export { createUserModel };
//# sourceMappingURL=user.es.js.map
