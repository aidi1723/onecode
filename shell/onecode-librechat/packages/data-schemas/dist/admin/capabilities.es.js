import { ResourceType } from 'librechat-data-provider';

// ---------------------------------------------------------------------------
// System Capabilities
// ---------------------------------------------------------------------------
/**
 * The canonical set of base system capabilities.
 *
 * These are used by the admin panel and LibreChat API to gate access to
 * admin features. Config-section-derived capabilities (e.g.
 * `manage:configs:endpoints`) are built on top of these where the
 * configSchema is available.
 */
const SystemCapabilities = {
    ACCESS_ADMIN: 'access:admin',
    READ_USERS: 'read:users',
    MANAGE_USERS: 'manage:users',
    READ_GROUPS: 'read:groups',
    MANAGE_GROUPS: 'manage:groups',
    READ_ROLES: 'read:roles',
    MANAGE_ROLES: 'manage:roles',
    READ_CONFIGS: 'read:configs',
    MANAGE_CONFIGS: 'manage:configs',
    ASSIGN_CONFIGS: 'assign:configs',
    READ_USAGE: 'read:usage',
    READ_AGENTS: 'read:agents',
    MANAGE_AGENTS: 'manage:agents',
    MANAGE_MCP_SERVERS: 'manage:mcpservers',
    READ_PROMPTS: 'read:prompts',
    MANAGE_PROMPTS: 'manage:prompts',
    READ_SKILLS: 'read:skills',
    MANAGE_SKILLS: 'manage:skills',
    /** Reserved — not yet enforced by any middleware. */
    READ_ASSISTANTS: 'read:assistants',
    MANAGE_ASSISTANTS: 'manage:assistants',
};
/**
 * Capabilities that are implied by holding a broader capability.
 * e.g. `MANAGE_USERS` implies `READ_USERS`.
 */
const CapabilityImplications = {
    [SystemCapabilities.MANAGE_USERS]: [SystemCapabilities.READ_USERS],
    [SystemCapabilities.MANAGE_GROUPS]: [SystemCapabilities.READ_GROUPS],
    [SystemCapabilities.MANAGE_ROLES]: [SystemCapabilities.READ_ROLES],
    [SystemCapabilities.MANAGE_CONFIGS]: [SystemCapabilities.READ_CONFIGS],
    [SystemCapabilities.MANAGE_AGENTS]: [SystemCapabilities.READ_AGENTS],
    [SystemCapabilities.MANAGE_PROMPTS]: [SystemCapabilities.READ_PROMPTS],
    [SystemCapabilities.MANAGE_SKILLS]: [SystemCapabilities.READ_SKILLS],
    [SystemCapabilities.MANAGE_ASSISTANTS]: [SystemCapabilities.READ_ASSISTANTS],
};
// ---------------------------------------------------------------------------
// Capability validation
// ---------------------------------------------------------------------------
const baseCapabilitySet = new Set(Object.values(SystemCapabilities));
const sectionCapPattern = /^(?:manage|read):configs:\w+$/;
const assignCapPattern = /^assign:configs:(?:user|group|role)$/;
/**
 * Runtime validator for the full `SystemCapability` union:
 * base capabilities, section-level config capabilities, and config assignment capabilities.
 */
function isValidCapability(value) {
    return (baseCapabilitySet.has(value) || sectionCapPattern.test(value) || assignCapPattern.test(value));
}
// ---------------------------------------------------------------------------
// Capability utility functions
// ---------------------------------------------------------------------------
/** Reverse map: for a given read capability, which manage capabilities imply it? */
const impliedByMap = {};
for (const [manage, reads] of Object.entries(CapabilityImplications)) {
    for (const read of reads) {
        if (!impliedByMap[read]) {
            impliedByMap[read] = [];
        }
        impliedByMap[read].push(manage);
    }
}
/**
 * Check whether a set of held capabilities satisfies a required capability,
 * accounting for the manage→read implication hierarchy.
 */
function hasImpliedCapability(held, required) {
    if (held.includes(required)) {
        return true;
    }
    const impliers = impliedByMap[required];
    if (impliers) {
        for (const cap of impliers) {
            if (held.includes(cap)) {
                return true;
            }
        }
    }
    return false;
}
/**
 * Given a set of directly-held capabilities, compute the full set including
 * all implied capabilities.
 */
function expandImplications(directCaps) {
    const expanded = new Set(directCaps);
    for (const cap of directCaps) {
        const implied = CapabilityImplications[cap];
        if (implied) {
            for (const imp of implied) {
                expanded.add(imp);
            }
        }
    }
    return Array.from(expanded);
}
// ---------------------------------------------------------------------------
// Resource & config capability mappings
// ---------------------------------------------------------------------------
/**
 * Maps each ACL ResourceType to the SystemCapability that grants
 * unrestricted management access. Typed as `Record<ResourceType, …>`
 * so adding a new ResourceType variant causes a compile error until a
 * capability is assigned here.
 */
const ResourceCapabilityMap = {
    [ResourceType.AGENT]: SystemCapabilities.MANAGE_AGENTS,
    [ResourceType.PROMPTGROUP]: SystemCapabilities.MANAGE_PROMPTS,
    [ResourceType.MCPSERVER]: SystemCapabilities.MANAGE_MCP_SERVERS,
    [ResourceType.REMOTE_AGENT]: SystemCapabilities.MANAGE_AGENTS,
    [ResourceType.SKILL]: SystemCapabilities.MANAGE_SKILLS,
};
/**
 * Derives a section-level config management capability from a configSchema key.
 * @example configCapability('endpoints') → 'manage:configs:endpoints'
 *
 * TODO: Section-level config capabilities are scaffolded but not yet active.
 * To activate delegated config management:
 *  1. Expose POST/DELETE /api/admin/grants endpoints (wiring grantCapability/revokeCapability)
 *  2. Seed section-specific grants for delegated admin roles via those endpoints
 *  3. Guard config write handlers with hasConfigCapability(user, section)
 */
function configCapability(section) {
    return `manage:configs:${section}`;
}
/**
 * Derives a section-level config read capability from a configSchema key.
 * @example readConfigCapability('endpoints') → 'read:configs:endpoints'
 */
function readConfigCapability(section) {
    return `read:configs:${section}`;
}
// ---------------------------------------------------------------------------
// Reserved principal IDs
// ---------------------------------------------------------------------------
/** Reserved principalId for the DB base config (overrides YAML defaults). */
const BASE_CONFIG_PRINCIPAL_ID = '__base__';
/** Pre-defined UI categories for grouping capabilities in the admin panel. */
const CAPABILITY_CATEGORIES = [
    {
        key: 'users',
        labelKey: 'com_cap_cat_users',
        capabilities: [SystemCapabilities.MANAGE_USERS, SystemCapabilities.READ_USERS],
    },
    {
        key: 'groups',
        labelKey: 'com_cap_cat_groups',
        capabilities: [SystemCapabilities.MANAGE_GROUPS, SystemCapabilities.READ_GROUPS],
    },
    {
        key: 'roles',
        labelKey: 'com_cap_cat_roles',
        capabilities: [SystemCapabilities.MANAGE_ROLES, SystemCapabilities.READ_ROLES],
    },
    {
        key: 'config',
        labelKey: 'com_cap_cat_config',
        capabilities: [
            SystemCapabilities.MANAGE_CONFIGS,
            SystemCapabilities.READ_CONFIGS,
            SystemCapabilities.ASSIGN_CONFIGS,
        ],
    },
    {
        key: 'content',
        labelKey: 'com_cap_cat_content',
        capabilities: [
            SystemCapabilities.MANAGE_AGENTS,
            SystemCapabilities.READ_AGENTS,
            SystemCapabilities.MANAGE_PROMPTS,
            SystemCapabilities.READ_PROMPTS,
            SystemCapabilities.MANAGE_SKILLS,
            SystemCapabilities.READ_SKILLS,
            SystemCapabilities.MANAGE_ASSISTANTS,
            SystemCapabilities.READ_ASSISTANTS,
            SystemCapabilities.MANAGE_MCP_SERVERS,
        ],
    },
    {
        key: 'system',
        labelKey: 'com_cap_cat_system',
        capabilities: [SystemCapabilities.ACCESS_ADMIN, SystemCapabilities.READ_USAGE],
    },
];

export { BASE_CONFIG_PRINCIPAL_ID, CAPABILITY_CATEGORIES, CapabilityImplications, ResourceCapabilityMap, SystemCapabilities, configCapability, expandImplications, hasImpliedCapability, isValidCapability, readConfigCapability };
//# sourceMappingURL=capabilities.es.js.map
