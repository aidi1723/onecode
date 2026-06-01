import { ResourceType, SKILL_NAME_MAX_LENGTH, SKILL_NAME_PATTERN as SKILL_NAME_PATTERN$1, SKILL_DESCRIPTION_MAX_LENGTH, SKILL_BODY_MAX_LENGTH, SKILL_DISPLAY_TITLE_MAX_LENGTH, SKILL_DESCRIPTION_SHORT_THRESHOLD as SKILL_DESCRIPTION_SHORT_THRESHOLD$1 } from 'librechat-data-provider';
import { isValidObjectIdString } from '../utils/objectId.es.js';
import { tenantSafeBulkWrite } from '../utils/tenantBulkWrite.es.js';
import { stripYamlTrailingComment } from '../utils/yaml.es.js';
import { escapeRegExp } from '../utils/string.es.js';
import logger from '../config/winston.es.js';

/** Partition an issue list into blocking errors and non-blocking warnings. */
function partitionIssues(issues) {
    const errors = [];
    const warnings = [];
    for (const issue of issues) {
        if (issue.severity === 'warning') {
            warnings.push(issue);
        }
        else {
            errors.push(issue);
        }
    }
    return { errors, warnings };
}
const SKILL_NAME_MAX = SKILL_NAME_MAX_LENGTH;
const SKILL_DESCRIPTION_MAX = SKILL_DESCRIPTION_MAX_LENGTH;
const SKILL_DESCRIPTION_SHORT_THRESHOLD = SKILL_DESCRIPTION_SHORT_THRESHOLD$1;
const SKILL_DISPLAY_TITLE_MAX = SKILL_DISPLAY_TITLE_MAX_LENGTH;
const SKILL_BODY_MAX = SKILL_BODY_MAX_LENGTH;
const SKILL_FILE_PATH_MAX = 500;
const SKILL_NAME_PATTERN = SKILL_NAME_PATTERN$1;
const RELATIVE_PATH_CHARS = /^[a-zA-Z0-9._\-/]+$/;
/**
 * Brand namespaces reserved for Anthropic-published skills and first-party
 * bundles. Matched as prefixes, so `anthropic-helper` is rejected but
 * `research-anthropic-helper` is fine.
 */
const RESERVED_NAME_PREFIXES = ['anthropic-', 'claude-'];
/**
 * Slash-command names that collide with LibreChat / Claude Code CLI commands.
 * A skill with one of these names would shadow a real command in any
 * slash-command UI. Matched exactly (not as prefix).
 */
const RESERVED_NAME_WORDS = new Set([
    'help',
    'clear',
    'compact',
    'model',
    'exit',
    'quit',
    'settings',
    'anthropic',
    'claude',
]);
function validateSkillName(name) {
    const issues = [];
    if (typeof name !== 'string' || name.length === 0) {
        issues.push({ field: 'name', code: 'REQUIRED', message: 'Name is required' });
        return issues;
    }
    if (name.length > SKILL_NAME_MAX) {
        issues.push({
            field: 'name',
            code: 'TOO_LONG',
            message: `Name must be ${SKILL_NAME_MAX} characters or less`,
        });
    }
    if (!SKILL_NAME_PATTERN.test(name)) {
        issues.push({
            field: 'name',
            code: 'INVALID_FORMAT',
            message: 'Name must be kebab-case: start with a lowercase letter or digit and contain only lowercase letters, digits, and hyphens',
        });
    }
    const lowered = name.toLowerCase();
    if (RESERVED_NAME_PREFIXES.some((prefix) => lowered.startsWith(prefix))) {
        issues.push({
            field: 'name',
            code: 'RESERVED_PREFIX',
            message: `Name cannot start with ${RESERVED_NAME_PREFIXES.map((p) => `"${p}"`).join(' or ')}`,
        });
    }
    if (RESERVED_NAME_WORDS.has(lowered)) {
        issues.push({
            field: 'name',
            code: 'RESERVED_WORD',
            message: `"${name}" is a reserved name`,
        });
    }
    return issues;
}
function validateSkillDescription(description) {
    const issues = [];
    if (typeof description !== 'string' || description.trim().length === 0) {
        issues.push({
            field: 'description',
            code: 'REQUIRED',
            message: 'Description is required',
        });
        return issues;
    }
    if (description.length > SKILL_DESCRIPTION_MAX) {
        issues.push({
            field: 'description',
            code: 'TOO_LONG',
            message: `Description must be ${SKILL_DESCRIPTION_MAX} characters or less`,
        });
    }
    if (description.trim().length < SKILL_DESCRIPTION_SHORT_THRESHOLD) {
        issues.push({
            field: 'description',
            code: 'TOO_SHORT',
            severity: 'warning',
            message: 'Short descriptions may cause Claude to miss triggering opportunities — aim for a concrete "when to use this skill" sentence.',
        });
    }
    return issues;
}
function validateSkillBody(body) {
    const issues = [];
    if (body !== undefined && typeof body !== 'string') {
        issues.push({ field: 'body', code: 'INVALID_TYPE', message: 'Body must be a string' });
        return issues;
    }
    if (typeof body === 'string' && body.length > SKILL_BODY_MAX) {
        issues.push({
            field: 'body',
            code: 'TOO_LONG',
            message: `Body must be ${SKILL_BODY_MAX} characters or less`,
        });
    }
    return issues;
}
function validateSkillDisplayTitle(displayTitle) {
    if (displayTitle === undefined || displayTitle === null) {
        return [];
    }
    if (typeof displayTitle !== 'string') {
        return [
            { field: 'displayTitle', code: 'INVALID_TYPE', message: 'Display title must be a string' },
        ];
    }
    if (displayTitle.length > SKILL_DISPLAY_TITLE_MAX) {
        return [
            {
                field: 'displayTitle',
                code: 'TOO_LONG',
                message: `Display title must be ${SKILL_DISPLAY_TITLE_MAX} characters or less`,
            },
        ];
    }
    return [];
}
/**
 * Validate the top-level `alwaysApply` column input. Mirrors the boolean
 * check on `frontmatter['always-apply']` so a loosely-typed API caller
 * sending `{"alwaysApply": "false"}` (string) gets a clean 400 at the
 * validation boundary instead of relying on Mongoose casting quirks to
 * coerce the value.
 *
 * `undefined` is the only pass-through value (meaning "don't touch this
 * field"). `null` is rejected: PATCH forwards any non-`undefined` value
 * straight into `$set`, so a `null` payload would persist `null` in a
 * boolean column, leaving the skill in a state that is neither "on" nor
 * "off" while `listAlwaysApplySkills` only matches `true`.
 */
function validateAlwaysApply(alwaysApply) {
    if (alwaysApply === undefined) {
        return [];
    }
    if (typeof alwaysApply !== 'boolean') {
        return [
            {
                field: 'alwaysApply',
                code: 'INVALID_TYPE',
                message: 'alwaysApply must be a boolean',
            },
        ];
    }
    return [];
}
/**
 * Known fields allowed inside a skill's YAML frontmatter. Anything else is
 * rejected in strict mode. The list is derived from Anthropic's Agent Skills
 * spec plus the fields LibreChat needs to pass through (`name`/`description`
 * are duplicated from the top-level columns because real `SKILL.md` files
 * include them in their frontmatter block).
 */
const ALLOWED_FRONTMATTER_KEYS = new Set([
    'name',
    'description',
    'when-to-use',
    'allowed-tools',
    'arguments',
    'argument-hint',
    'user-invocable',
    'disable-model-invocation',
    'always-apply',
    'model',
    'effort',
    'context',
    'agent',
    'paths',
    'shell',
    'hooks',
    'version',
    'metadata',
]);
const FRONTMATTER_MAX_STRING = 2000;
const FRONTMATTER_MAX_ARRAY = 100;
const FRONTMATTER_MAX_DEPTH = 4;
const FRONTMATTER_KIND = {
    name: 'string',
    description: 'string',
    'when-to-use': 'string',
    'allowed-tools': ['string', 'stringArray'],
    arguments: ['string', 'stringArray'],
    'argument-hint': 'string',
    'user-invocable': 'boolean',
    'disable-model-invocation': 'boolean',
    'always-apply': 'boolean',
    model: 'string',
    effort: ['string', 'number'],
    context: 'string',
    agent: 'string',
    paths: ['string', 'stringArray'],
    shell: 'string',
    version: 'string',
};
function isPlainObject(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function isStringArray(value) {
    return (Array.isArray(value) &&
        value.length <= FRONTMATTER_MAX_ARRAY &&
        value.every((v) => typeof v === 'string' && v.length <= FRONTMATTER_MAX_STRING));
}
function matchesKind(value, kind) {
    if (kind === 'string') {
        return typeof value === 'string' && value.length <= FRONTMATTER_MAX_STRING;
    }
    if (kind === 'number') {
        return typeof value === 'number' && Number.isFinite(value);
    }
    if (kind === 'boolean') {
        return typeof value === 'boolean';
    }
    return isStringArray(value);
}
/**
 * Shallow structural sanity check for `hooks`/`metadata` objects. We don't
 * know their full schema yet, so we just verify they are plain objects with
 * JSON-serializable leaf values up to a max depth — enough to block pathological
 * payloads without constraining legitimate frontmatter extensions.
 */
function isJsonSafe(value, depth) {
    if (depth > FRONTMATTER_MAX_DEPTH) {
        return false;
    }
    if (value === null)
        return true;
    const t = typeof value;
    if (t === 'string')
        return value.length <= FRONTMATTER_MAX_STRING;
    if (t === 'number')
        return Number.isFinite(value);
    if (t === 'boolean')
        return true;
    if (Array.isArray(value)) {
        if (value.length > FRONTMATTER_MAX_ARRAY)
            return false;
        return value.every((v) => isJsonSafe(v, depth + 1));
    }
    if (isPlainObject(value)) {
        return Object.values(value).every((v) => isJsonSafe(v, depth + 1));
    }
    return false;
}
/**
 * Validate a skill's structured YAML frontmatter. Strict mode: unknown keys
 * are rejected so any expansion of the allowed set is an intentional code
 * change. Known keys are type-checked against `FRONTMATTER_KIND`; `hooks` and
 * `metadata` fall back to a shallow JSON-safety check because their full
 * schemas live outside this module.
 */
function validateSkillFrontmatter(frontmatter) {
    if (frontmatter === undefined || frontmatter === null) {
        return [];
    }
    if (!isPlainObject(frontmatter)) {
        return [
            {
                field: 'frontmatter',
                code: 'INVALID_TYPE',
                message: 'Frontmatter must be a plain object',
            },
        ];
    }
    const issues = [];
    for (const [key, value] of Object.entries(frontmatter)) {
        if (!ALLOWED_FRONTMATTER_KEYS.has(key)) {
            issues.push({
                field: `frontmatter.${key}`,
                code: 'UNKNOWN_KEY',
                message: `"${key}" is not a recognized frontmatter key`,
            });
            continue;
        }
        if (key === 'hooks' || key === 'metadata') {
            if (!isPlainObject(value) || !isJsonSafe(value, 0)) {
                issues.push({
                    field: `frontmatter.${key}`,
                    code: 'INVALID_SHAPE',
                    message: `"${key}" must be a plain JSON-safe object (max depth ${FRONTMATTER_MAX_DEPTH}, max string ${FRONTMATTER_MAX_STRING})`,
                });
            }
            continue;
        }
        const expected = FRONTMATTER_KIND[key];
        if (!expected) {
            continue;
        }
        const kinds = Array.isArray(expected) ? expected : [expected];
        if (!kinds.some((kind) => matchesKind(value, kind))) {
            issues.push({
                field: `frontmatter.${key}`,
                code: 'INVALID_TYPE',
                message: `"${key}" must be ${kinds.join(' or ')}`,
            });
        }
    }
    return issues;
}
function validateRelativePath(relativePath) {
    const issues = [];
    if (typeof relativePath !== 'string' || relativePath.length === 0) {
        issues.push({
            field: 'relativePath',
            code: 'REQUIRED',
            message: 'Relative path is required',
        });
        return issues;
    }
    if (relativePath.length > SKILL_FILE_PATH_MAX) {
        issues.push({
            field: 'relativePath',
            code: 'TOO_LONG',
            message: `Relative path must be ${SKILL_FILE_PATH_MAX} characters or less`,
        });
    }
    if (relativePath.startsWith('/') || relativePath.startsWith('\\')) {
        issues.push({
            field: 'relativePath',
            code: 'ABSOLUTE_PATH',
            message: 'Relative path must not start with a slash',
        });
    }
    if (!RELATIVE_PATH_CHARS.test(relativePath)) {
        issues.push({
            field: 'relativePath',
            code: 'INVALID_CHARS',
            message: 'Relative path contains invalid characters',
        });
    }
    const segments = relativePath.split('/');
    if (segments.some((s) => s === '' || s === '.' || s === '..')) {
        issues.push({
            field: 'relativePath',
            code: 'TRAVERSAL',
            message: 'Relative path cannot contain empty segments or "." / ".."',
        });
    }
    if (relativePath === 'SKILL.md' || segments[0] === 'SKILL.md') {
        issues.push({
            field: 'relativePath',
            code: 'RESERVED',
            message: 'SKILL.md is managed via the skill body, not file uploads',
        });
    }
    return issues;
}
function inferSkillFileCategory(relativePath) {
    const [top] = relativePath.split('/');
    if (top === 'scripts')
        return 'script';
    if (top === 'references')
        return 'reference';
    if (top === 'assets')
        return 'asset';
    return 'other';
}
/**
 * Maps the runtime-enforced frontmatter fields onto their first-class
 * column equivalents. Returns only the keys that were explicitly set on the
 * frontmatter so callers can decide whether to write `undefined` (skip the
 * `$set`) versus a concrete value.
 *
 * `allowed-tools` accepts string or string[] per the validator; both are
 * normalized to an array. Empty strings are filtered out so a stray comma
 * in YAML doesn't leak through as `''`.
 */
function deriveStructuredFrontmatterFields(frontmatter) {
    if (!frontmatter || typeof frontmatter !== 'object') {
        return {};
    }
    const derived = {};
    const disableModelInvocationRaw = frontmatter['disable-model-invocation'];
    if (typeof disableModelInvocationRaw === 'boolean') {
        derived.disableModelInvocation = disableModelInvocationRaw;
    }
    const userInvocableRaw = frontmatter['user-invocable'];
    if (typeof userInvocableRaw === 'boolean') {
        derived.userInvocable = userInvocableRaw;
    }
    const allowedToolsRaw = frontmatter['allowed-tools'];
    if (typeof allowedToolsRaw === 'string') {
        /**
         * YAML scalars like `allowed-tools: web_search` are parsed as a single
         * string. Wrap into a one-element array; we deliberately do NOT split
         * on commas — the validator already accepts string-array form and
         * trying to "be helpful" by splitting `"web_search, file_search"`
         * would silently invent semantics the spec doesn't promise.
         */
        if (allowedToolsRaw.length > 0) {
            derived.allowedTools = [allowedToolsRaw];
        }
    }
    else if (Array.isArray(allowedToolsRaw)) {
        derived.allowedTools = allowedToolsRaw.filter((entry) => typeof entry === 'string' && entry.length > 0);
    }
    return derived;
}
/**
 * Read-time fallback for skills authored before the structured columns
 * existed: if the column is unset but the matching key is present in
 * `frontmatter`, fill the column in on the returned object so downstream
 * runtime checks (`skill.userInvocable === false`,
 * `skill.disableModelInvocation === true`, `skill.allowedTools`) behave
 * the same way they would for a freshly-created skill.
 *
 * Side-effect-free w.r.t. the DB (no writes), but mutates its argument
 * in place and returns the same reference. Callers passing a `lean()`
 * doc this is fine — the doc is a fresh JS object owned by the caller.
 * When the skill is next updated, `updateSkill` re-derives and persists
 * the columns naturally, so this fallback gradually becomes a no-op.
 *
 * Skills with the columns already populated short-circuit to no-op.
 */
function backfillDerivedFromFrontmatter(skill) {
    if (!skill || !skill.frontmatter) {
        return skill;
    }
    const derived = deriveStructuredFrontmatterFields(skill.frontmatter);
    if (skill.disableModelInvocation === undefined && derived.disableModelInvocation !== undefined) {
        skill.disableModelInvocation = derived.disableModelInvocation;
    }
    if (skill.userInvocable === undefined && derived.userInvocable !== undefined) {
        skill.userInvocable = derived.userInvocable;
    }
    if (skill.allowedTools === undefined && derived.allowedTools !== undefined) {
        skill.allowedTools = derived.allowedTools;
    }
    return skill;
}
/**
 * Extractor for the `always-apply` flag sitting inside a SKILL.md body's
 * YAML frontmatter block. The REST edit flow lets users rewrite the full
 * SKILL.md text via `update.body` without a structured `frontmatter`
 * object, so this is the only signal we have for "user flipped
 * `always-apply:` inline in their editor".
 *
 * Returns a discriminated union so callers can tell:
 *  - `absent` — no `always-apply:` key (leave column alone; could be
 *    "user removed the flag" or "user hasn't written it yet" — both
 *    resolve to no-op). An empty value (`always-apply:` with nothing
 *    after the colon) is also treated as absent to allow mid-edit
 *    placeholder states without rejecting a save.
 *  - `valid` — parsed cleanly as `true` / `false` (case-insensitive,
 *    quote-tolerant, YAML inline-comment-tolerant).
 *  - `invalid` — key is present with a non-empty value that isn't a
 *    recognizable boolean (e.g. `tru`, `yes`, `1`). Validation rejects
 *    this rather than silently ignoring so `always-apply: tru` typos
 *    surface as 400s instead of drifting the column from what the
 *    saved SKILL.md text says.
 */
function extractAlwaysApplyFromBody(body) {
    if (typeof body !== 'string' || body.length === 0) {
        return { status: 'absent' };
    }
    const trimmed = body.trim();
    if (!trimmed.startsWith('---')) {
        return { status: 'absent' };
    }
    const after = trimmed.slice(3);
    const closingIdx = after.indexOf('\n---');
    if (closingIdx === -1) {
        return { status: 'absent' };
    }
    const block = after.slice(0, closingIdx);
    for (const line of block.split('\n')) {
        const colon = line.indexOf(':');
        if (colon === -1) {
            continue;
        }
        const key = line.slice(0, colon).trim().toLowerCase();
        if (key !== 'always-apply') {
            continue;
        }
        // Strip the YAML inline comment BEFORE unquoting — a line like
        // `always-apply: "true" # note` has both, and if we only handled
        // whole-line quoting first, the quoted branch wouldn't match and
        // the comment-strip would leave `"true"` which parses as invalid.
        let value = stripYamlTrailingComment(line.slice(colon + 1).trim()).trim();
        if (value === '') {
            return { status: 'absent' };
        }
        if (value.length >= 2 &&
            ((value[0] === '"' && value[value.length - 1] === '"') ||
                (value[0] === "'" && value[value.length - 1] === "'"))) {
            value = value.slice(1, -1);
        }
        value = value.trim();
        if (value === '') {
            return { status: 'absent' };
        }
        const lowered = value.toLowerCase();
        if (lowered === 'true')
            return { status: 'valid', value: true };
        if (lowered === 'false')
            return { status: 'valid', value: false };
        return { status: 'invalid' };
    }
    return { status: 'absent' };
}
/**
 * Resolve the effective `alwaysApply` boolean for a create/update call.
 *
 * The indexed `alwaysApply` column is the source of truth for auto-priming
 * queries; it can also be carried inline inside the SKILL.md `body` or in
 * the structured `frontmatter` bag. All three surfaces must stay in sync
 * or a skill edit that flips `always-apply:` in the body would leave the
 * column stale and the UI / auto-priming query would use the old value.
 *
 * Precedence:
 *  1. An explicit top-level `alwaysApply` wins (caller overrides).
 *  2. Otherwise, derive from `frontmatter['always-apply']` when it is
 *     a strict boolean.
 *  3. Otherwise, parse `always-apply:` out of the SKILL.md body
 *     frontmatter block (covers the UI edit flow that sends only
 *     `body` without a structured `frontmatter` object).
 *  4. Otherwise, return `fallback` (typically `false` on create, or the
 *     current column value on update so an update that doesn't touch
 *     any of the three sources leaves the column alone).
 */
function resolveAlwaysApplyFromInput(explicit, frontmatter, body, fallback, 
/* Callers that have already parsed the body (e.g. because they also
   ran body-level validation) can thread the result in to avoid a
   second parse. Leave undefined to let the helper parse on demand. */
precomputedBody) {
    if (typeof explicit === 'boolean') {
        return explicit;
    }
    const fromFrontmatter = frontmatter === null || frontmatter === void 0 ? void 0 : frontmatter['always-apply'];
    if (typeof fromFrontmatter === 'boolean') {
        return fromFrontmatter;
    }
    const fromBody = precomputedBody !== null && precomputedBody !== void 0 ? precomputedBody : extractAlwaysApplyFromBody(body);
    if (fromBody.status === 'valid') {
        return fromBody.value;
    }
    return fallback;
}
function createSkillMethods(mongoose, deps) {
    const { ObjectId } = mongoose.Types;
    function buildSkillFilter(params) {
        const filter = {
            _id: { $in: params.accessibleIds },
        };
        if (params.category && params.category.length > 0) {
            filter.category = params.category;
        }
        if (params.search && params.search.length > 0) {
            const rx = new RegExp(escapeRegExp(params.search), 'i');
            filter.$or = [{ name: rx }, { description: rx }, { displayTitle: rx }];
        }
        return filter;
    }
    function decodeCursor(cursor) {
        if (!cursor || cursor === 'undefined' || cursor === 'null') {
            return null;
        }
        try {
            const decoded = JSON.parse(Buffer.from(cursor, 'base64').toString('utf8'));
            if (!decoded.updatedAt ||
                !decoded._id ||
                Number.isNaN(new Date(decoded.updatedAt).getTime()) ||
                !isValidObjectIdString(decoded._id)) {
                return null;
            }
            return { updatedAt: new Date(decoded.updatedAt), _id: new ObjectId(decoded._id) };
        }
        catch (error) {
            logger.warn(`[skill.decodeCursor] Invalid cursor: ${error.message}`);
            return null;
        }
    }
    function encodeCursor(row) {
        return Buffer.from(JSON.stringify({ updatedAt: row.updatedAt.toISOString(), _id: row._id.toString() })).toString('base64');
    }
    async function createSkill(data) {
        var _a, _b, _c, _d, _e, _f;
        /* Parse body's always-apply status once — reused for validation
           (below) and derivation in `resolveAlwaysApplyFromInput`. Avoids
           parsing the same YAML frontmatter block twice per create. */
        const bodyAlwaysApply = data.body !== undefined ? extractAlwaysApplyFromBody(data.body) : undefined;
        const issues = [
            ...validateSkillName(data.name),
            ...validateSkillDescription(data.description),
            ...validateSkillBody(data.body),
            ...validateSkillDisplayTitle(data.displayTitle),
            ...validateSkillFrontmatter(data.frontmatter),
            ...validateAlwaysApply(data.alwaysApply),
        ];
        /* Body-level `always-apply:` only needs to be well-formed when a
           higher-precedence source won't override it (see
           `resolveAlwaysApplyFromInput` for the cascade). A caller sending
           an explicit top-level `alwaysApply` or a structured
           `frontmatter['always-apply']` has the body value overridden at
           derivation time, so rejecting them for a typo they aren't relying
           on would be user-hostile. */
        if ((bodyAlwaysApply === null || bodyAlwaysApply === void 0 ? void 0 : bodyAlwaysApply.status) === 'invalid' &&
            typeof data.alwaysApply !== 'boolean' &&
            typeof ((_a = data.frontmatter) === null || _a === void 0 ? void 0 : _a['always-apply']) !== 'boolean') {
            issues.push({
                field: 'body.frontmatter.always-apply',
                code: 'INVALID_TYPE',
                message: '"always-apply" in SKILL.md frontmatter must be a boolean (true or false)',
            });
        }
        const { errors, warnings } = partitionIssues(issues);
        if (errors.length > 0) {
            const error = new Error('Skill validation failed');
            error.issues = errors;
            error.code = 'SKILL_VALIDATION_FAILED';
            throw error;
        }
        const Skill = mongoose.models.Skill;
        // Application-level uniqueness check on (name, author, tenantId).
        // The unique index in the schema is the persistent guarantee, but Mongoose
        // creates indexes asynchronously and tests can race ahead of index creation,
        // so we also enforce it here for deterministic behavior and a clean error.
        const existing = await Skill.findOne({
            name: data.name,
            author: data.author,
            tenantId: (_b = data.tenantId) !== null && _b !== void 0 ? _b : null,
        })
            .select('_id')
            .lean();
        if (existing) {
            const error = new Error(`A skill with name "${data.name}" already exists for this author`);
            error.code = 11000;
            throw error;
        }
        const derived = deriveStructuredFrontmatterFields(data.frontmatter);
        const doc = await Skill.create({
            name: data.name,
            displayTitle: data.displayTitle,
            description: data.description,
            body: (_c = data.body) !== null && _c !== void 0 ? _c : '',
            frontmatter: (_d = data.frontmatter) !== null && _d !== void 0 ? _d : {},
            category: (_e = data.category) !== null && _e !== void 0 ? _e : '',
            author: data.author,
            authorName: data.authorName,
            version: 1,
            source: (_f = data.source) !== null && _f !== void 0 ? _f : 'inline',
            sourceMetadata: data.sourceMetadata,
            fileCount: 0,
            alwaysApply: resolveAlwaysApplyFromInput(data.alwaysApply, data.frontmatter, data.body, false, bodyAlwaysApply),
            tenantId: data.tenantId,
            ...derived,
        });
        return {
            skill: doc.toObject(),
            warnings,
        };
    }
    async function getSkillById(id) {
        var _a;
        if (typeof id === 'string' && !isValidObjectIdString(id)) {
            return null;
        }
        const Skill = mongoose.models.Skill;
        const doc = await Skill.findById(id).lean();
        return (_a = doc) !== null && _a !== void 0 ? _a : null;
    }
    async function getSkillByName(name, accessibleIds, options) {
        var _a;
        const Skill = mongoose.models.Skill;
        const preferUserInvocable = (options === null || options === void 0 ? void 0 : options.preferUserInvocable) === true;
        const preferModelInvocable = (options === null || options === void 0 ? void 0 : options.preferModelInvocable) === true;
        /* Single-doc fast path when no preference is requested — preserves
           the previous performance characteristics for callers that just
           want "newest match". */
        if (!preferUserInvocable && !preferModelInvocable) {
            const doc = await Skill.findOne({ name, _id: { $in: accessibleIds } })
                .sort({ updatedAt: -1 })
                .lean();
            return backfillDerivedFromFrontmatter((_a = doc) !== null && _a !== void 0 ? _a : null);
        }
        /* Multi-doc path: fetch all matching docs (typically 1, rarely 2+
           across same-name duplicates) and pick the first satisfying the
           caller's preference; fall back to newest. */
        const docs = (await Skill.find({ name, _id: { $in: accessibleIds } })
            .sort({ updatedAt: -1 })
            .lean());
        if (docs.length === 0) {
            return null;
        }
        for (const doc of docs) {
            backfillDerivedFromFrontmatter(doc);
        }
        const preferred = docs.find((d) => {
            if (preferUserInvocable && d.userInvocable === false) {
                return false;
            }
            if (preferModelInvocable && d.disableModelInvocation === true) {
                return false;
            }
            return true;
        });
        return preferred !== null && preferred !== void 0 ? preferred : docs[0];
    }
    async function listSkillsByAccess(params) {
        const Skill = mongoose.models.Skill;
        const limit = Math.min(Math.max(1, params.limit || 20), 100);
        const baseFilter = buildSkillFilter(params);
        const cursor = decodeCursor(params.cursor);
        let filter = baseFilter;
        if (cursor) {
            const cursorCondition = {
                $or: [
                    { updatedAt: { $lt: cursor.updatedAt } },
                    { updatedAt: cursor.updatedAt, _id: { $gt: cursor._id } },
                ],
            };
            filter = { $and: [baseFilter, cursorCondition] };
        }
        const rows = await Skill.find(filter)
            .sort({ updatedAt: -1, _id: 1 })
            .limit(limit + 1)
            /* `frontmatter` is deliberately NOT projected: the structured
               columns (disableModelInvocation / userInvocable / allowedTools /
               alwaysApply) are always populated by `createSkill` / `updateSkill`
               going forward, and the branch this code ships on never shipped
               to main — so no legacy rows exist that would need a frontmatter
               read-time backfill on summaries. Skipping it saves ~2KB/skill ×
               100/page of wire traffic. `backfillDerivedFromFrontmatter` is
               still called below as defensive code; it short-circuits when
               `frontmatter` is undefined. */
            .select('name displayTitle description category author authorName version source sourceMetadata fileCount alwaysApply tenantId disableModelInvocation userInvocable allowedTools createdAt updatedAt')
            .lean();
        /* Defensive read-time fallback. With `frontmatter` excluded from the
           projection, the helper short-circuits immediately; kept in the loop
           so a future projection change (or legacy rows appearing via a
           migration) continues to get runtime-column restoration for free. */
        for (const row of rows) {
            backfillDerivedFromFrontmatter(row);
        }
        const has_more = rows.length > limit;
        const sliced = has_more ? rows.slice(0, limit) : rows;
        const last = sliced[sliced.length - 1];
        const after = has_more && last
            ? encodeCursor({
                updatedAt: last.updatedAt,
                _id: last._id,
            })
            : null;
        return {
            skills: sliced,
            has_more,
            after,
        };
    }
    async function listAlwaysApplySkills(params) {
        const Skill = mongoose.models.Skill;
        if (!params.accessibleIds.length) {
            return { skills: [], has_more: false, after: null };
        }
        const limit = Math.min(Math.max(1, params.limit || 20), 100);
        const baseFilter = {
            _id: { $in: params.accessibleIds },
            alwaysApply: true,
        };
        const cursor = decodeCursor(params.cursor);
        let filter = baseFilter;
        if (cursor) {
            const cursorCondition = {
                $or: [
                    { updatedAt: { $lt: cursor.updatedAt } },
                    { updatedAt: cursor.updatedAt, _id: { $gt: cursor._id } },
                ],
            };
            filter = { $and: [baseFilter, cursorCondition] };
        }
        const rows = await Skill.find(filter)
            .sort({ updatedAt: -1, _id: 1 })
            .limit(limit + 1)
            .select('name body author updatedAt allowedTools')
            .lean();
        const has_more = rows.length > limit;
        const sliced = has_more ? rows.slice(0, limit) : rows;
        const last = sliced[sliced.length - 1];
        const after = has_more && last
            ? encodeCursor({
                updatedAt: last.updatedAt,
                _id: last._id,
            })
            : null;
        /**
         * `allowedTools` is projected alongside `name`/`body`/`author` so the
         * always-apply prime pipeline (post-Phase 6) can union skill-declared
         * tool allowlists into the agent's effective tool set for the turn —
         * same symmetry as the manual-prime path, which reads the column off
         * `getSkillByName`. Older rows predating the column show up with
         * `allowedTools === undefined` (the backfill helper runs on those at
         * read time elsewhere; per-turn priming is fine with undefined).
         */
        const skills = sliced.map((row) => {
            var _a;
            const result = {
                _id: row._id,
                name: row.name,
                body: (_a = row.body) !== null && _a !== void 0 ? _a : '',
                author: row.author,
            };
            if (row.allowedTools !== undefined) {
                result.allowedTools = row.allowedTools;
            }
            return result;
        });
        return { skills, has_more, after };
    }
    async function updateSkill(params) {
        var _a;
        const { id, expectedVersion, update } = params;
        if (!isValidObjectIdString(id)) {
            return { status: 'not_found' };
        }
        /* Parse body's always-apply status once — reused for validation
           (precedence-aware, below) and the derivation cascade further
           down. Avoids parsing the same YAML frontmatter block twice per
           update. */
        const bodyAlwaysApply = update.body !== undefined ? extractAlwaysApplyFromBody(update.body) : undefined;
        const issues = [];
        if (update.name !== undefined)
            issues.push(...validateSkillName(update.name));
        if (update.description !== undefined)
            issues.push(...validateSkillDescription(update.description));
        if (update.body !== undefined)
            issues.push(...validateSkillBody(update.body));
        if (update.displayTitle !== undefined)
            issues.push(...validateSkillDisplayTitle(update.displayTitle));
        if (update.frontmatter !== undefined)
            issues.push(...validateSkillFrontmatter(update.frontmatter));
        if (update.alwaysApply !== undefined)
            issues.push(...validateAlwaysApply(update.alwaysApply));
        /* Body-level `always-apply:` only needs to be well-formed when a
           higher-precedence source won't override it (see
           `resolveAlwaysApplyFromInput` for precedence). Rejecting a typo
           the caller is already overriding would be user-hostile, and the
           body-inline derivation branch below is skipped for those
           payloads anyway. */
        if ((bodyAlwaysApply === null || bodyAlwaysApply === void 0 ? void 0 : bodyAlwaysApply.status) === 'invalid' &&
            update.alwaysApply === undefined &&
            typeof ((_a = update.frontmatter) === null || _a === void 0 ? void 0 : _a['always-apply']) !== 'boolean') {
            issues.push({
                field: 'body.frontmatter.always-apply',
                code: 'INVALID_TYPE',
                message: '"always-apply" in SKILL.md frontmatter must be a boolean (true or false)',
            });
        }
        const { errors, warnings } = partitionIssues(issues);
        if (errors.length > 0) {
            const error = new Error('Skill validation failed');
            error.issues = errors;
            error.code = 'SKILL_VALIDATION_FAILED';
            throw error;
        }
        const Skill = mongoose.models.Skill;
        const setPayload = {};
        const unsetPayload = {};
        if (update.name !== undefined)
            setPayload.name = update.name;
        if (update.displayTitle !== undefined)
            setPayload.displayTitle = update.displayTitle;
        if (update.description !== undefined)
            setPayload.description = update.description;
        if (update.body !== undefined)
            setPayload.body = update.body;
        if (update.frontmatter !== undefined) {
            setPayload.frontmatter = update.frontmatter;
            /**
             * Derived columns track frontmatter — when frontmatter changes, the
             * derived view must follow. Fields the new frontmatter omits are
             * unset (back to schema default) so removing `disable-model-invocation`
             * from a SKILL.md re-enables model invocation on the next save.
             */
            const derived = deriveStructuredFrontmatterFields(update.frontmatter);
            for (const key of ['disableModelInvocation', 'userInvocable', 'allowedTools']) {
                if (derived[key] !== undefined) {
                    setPayload[key] = derived[key];
                }
                else {
                    unsetPayload[key] = '';
                }
            }
        }
        if (update.category !== undefined)
            setPayload.category = update.category;
        /**
         * Keep the indexed `alwaysApply` column in sync with whatever the update
         * is carrying: an explicit top-level `alwaysApply` always wins; a
         * structured `frontmatter` with `always-apply: true/false` is next; and
         * a `body` update is scanned last for an inline `always-apply:` line
         * inside the SKILL.md frontmatter block. The body path is load-bearing
         * for the REST edit flow — the current UI sends `body` without a
         * parallel `frontmatter` object, so inline edits to `always-apply:`
         * would otherwise leave the column stale and auto-priming / pin
         * badges would keep using the old value.
         *
         * When a `body` is submitted with NO `always-apply:` line (e.g. the
         * user removed the line from SKILL.md), that counts as a positive
         * declaration of "not always-apply" — the column flips to `false`.
         * Leaving it untouched would leave a skill that was once always-apply
         * silently auto-priming even after its own SKILL.md no longer
         * declares the flag.
         *
         * Important: the gates key off the *presence of an always-apply value*
         * at each level, not the presence of the parent field. An API caller
         * that sends both `body` and an unrelated `frontmatter` bag (e.g.
         * editing category + rewriting SKILL.md in one PATCH) still gets the
         * body-inline flag respected because `frontmatter['always-apply']`
         * is absent in that payload.
         */
        let derivedAlwaysApply;
        if (update.alwaysApply !== undefined) {
            derivedAlwaysApply = update.alwaysApply;
        }
        if (derivedAlwaysApply === undefined && update.frontmatter !== undefined) {
            const fromFrontmatter = update.frontmatter['always-apply'];
            if (typeof fromFrontmatter === 'boolean') {
                derivedAlwaysApply = fromFrontmatter;
            }
        }
        if (derivedAlwaysApply === undefined && bodyAlwaysApply !== undefined) {
            if (bodyAlwaysApply.status === 'valid') {
                derivedAlwaysApply = bodyAlwaysApply.value;
            }
            else if (bodyAlwaysApply.status === 'absent') {
                /* An `absent` result means the user submitted a new body that
                   declares no `always-apply:` key (either the key was removed or
                   no frontmatter block was ever there). The body is the
                   authoritative source for this skill's declared state: editing
                   it to drop the flag intends to turn auto-priming off, so flip
                   the column to `false`. Without this, a skill that was once
                   `alwaysApply: true` would keep auto-priming after the user
                   removed the declaration from SKILL.md — a persistent,
                   invisible mismatch between the file and runtime behavior.
                   `invalid` is rejected upstream by `validateAlwaysApplyInBody`
                   so this branch only handles the legitimate absence case. */
                derivedAlwaysApply = false;
            }
        }
        if (derivedAlwaysApply !== undefined) {
            setPayload.alwaysApply = derivedAlwaysApply;
        }
        const updateOps = {
            $set: setPayload,
            $inc: { version: 1 },
        };
        if (Object.keys(unsetPayload).length > 0) {
            updateOps.$unset = unsetPayload;
        }
        const result = await Skill.findOneAndUpdate({ _id: new ObjectId(id), version: expectedVersion }, updateOps, { new: true }).lean();
        if (result) {
            return {
                status: 'updated',
                skill: result,
                warnings,
            };
        }
        const current = await Skill.findById(id).lean();
        if (!current) {
            return { status: 'not_found' };
        }
        return {
            status: 'conflict',
            current: current,
        };
    }
    async function deleteSkill(id) {
        if (!isValidObjectIdString(id)) {
            return { deleted: false };
        }
        const Skill = mongoose.models.Skill;
        const SkillFile = mongoose.models.SkillFile;
        const objectId = new ObjectId(id);
        const res = await Skill.deleteOne({ _id: objectId });
        if (!res.deletedCount) {
            return { deleted: false };
        }
        await SkillFile.deleteMany({ skillId: objectId });
        try {
            await deps.removeAllPermissions({ resourceType: ResourceType.SKILL, resourceId: id });
        }
        catch (error) {
            logger.error(`[deleteSkill] Error removing permissions for ${id}:`, error);
        }
        return { deleted: true };
    }
    async function deleteUserSkills(userId) {
        var _a;
        const userObjectId = typeof userId === 'string' ? new ObjectId(userId) : userId;
        const Skill = mongoose.models.Skill;
        const soleOwned = await deps.getSoleOwnedResourceIds(userObjectId, ResourceType.SKILL);
        if (soleOwned.length === 0) {
            return 0;
        }
        const SkillFile = mongoose.models.SkillFile;
        await SkillFile.deleteMany({ skillId: { $in: soleOwned } });
        const res = await Skill.deleteMany({ _id: { $in: soleOwned } });
        await Promise.allSettled(soleOwned.map((rid) => deps
            .removeAllPermissions({
            resourceType: ResourceType.SKILL,
            resourceId: rid.toString(),
        })
            .catch((error) => logger.error(`[deleteUserSkills] Error removing permissions for ${rid}:`, error))));
        return (_a = res.deletedCount) !== null && _a !== void 0 ? _a : 0;
    }
    /**
     * Atomically bumps `Skill.version` and adjusts `fileCount` by `delta`.
     * `delta` is `+1` when a new file is inserted, `-1` when one is deleted, and
     * `0` when an existing file is replaced in place.
     *
     * NOTE on consistency: this runs as a **separate** MongoDB operation from
     * the `upsertSkillFile` / `deleteSkillFile` that triggers it. MongoDB only
     * provides multi-document ACID via transactions (which require a replica
     * set), and LibreChat does not currently require that deployment shape. In
     * the rare case where a SkillFile write succeeds but the subsequent
     * `findByIdAndUpdate` here fails (connection drop, primary failover mid-
     * request), the `fileCount` on the parent Skill will drift from the true
     * row count until the next successful upsert/delete corrects it. Options if
     * this ever shows up in practice:
     *   - wrap both ops in a transaction (requires a replica set)
     *   - periodic reconciliation: `fileCount = count(skill_files where skillId = ?)`
     *   - treat `fileCount` as advisory and recompute on read when accuracy
     *     matters
     * For phase 1, skill files are stubbed at the upload boundary, so the risk
     * window doesn't open in practice.
     */
    async function bumpSkillVersionAndAdjustFileCount(skillId, delta) {
        const Skill = mongoose.models.Skill;
        const updateOps = { $inc: { version: 1 } };
        if (delta !== 0) {
            updateOps.$inc.fileCount = delta;
        }
        await Skill.findByIdAndUpdate(skillId, updateOps);
    }
    async function listSkillFiles(skillId) {
        const SkillFile = mongoose.models.SkillFile;
        const rows = await SkillFile.find({ skillId })
            .select('-content')
            .sort({ relativePath: 1 })
            .lean();
        return rows;
    }
    async function upsertSkillFile(row) {
        var _a;
        const issues = validateRelativePath(row.relativePath);
        if (issues.length > 0) {
            const error = new Error('Skill file validation failed');
            error.issues = issues;
            error.code = 'SKILL_FILE_VALIDATION_FAILED';
            throw error;
        }
        const SkillFile = mongoose.models.SkillFile;
        const category = inferSkillFileCategory(row.relativePath);
        // Atomic new-vs-replace detection: with `new: false, upsert: true`,
        // `findOneAndUpdate` returns the pre-update document (or null if the doc
        // did not exist and was just inserted). Checking the return value replaces
        // a non-atomic `findOne` + `upsert` pair that could double-count on
        // concurrent uploads of the same (skillId, relativePath).
        const previous = await SkillFile.findOneAndUpdate({ skillId: row.skillId, relativePath: row.relativePath }, {
            $set: {
                skillId: row.skillId,
                relativePath: row.relativePath,
                file_id: row.file_id,
                filename: row.filename,
                filepath: row.filepath,
                storageKey: row.storageKey,
                storageRegion: row.storageRegion,
                source: row.source,
                mimeType: row.mimeType,
                bytes: row.bytes,
                category,
                isExecutable: (_a = row.isExecutable) !== null && _a !== void 0 ? _a : false,
                author: row.author,
                tenantId: row.tenantId,
            },
            $unset: { content: '', isBinary: '', codeEnvRef: '' },
        }, { new: false, upsert: true }).lean();
        const delta = previous ? 0 : 1;
        await bumpSkillVersionAndAdjustFileCount(row.skillId, delta);
        // Fetch the current (post-upsert) document for the caller. This second
        // round-trip is an intentional tradeoff for the TOCTOU-safe detection
        // above: `new: false` is required to distinguish insert from replace
        // atomically, which means `findOneAndUpdate` returns the pre-update
        // document (null on insert). A separate `findOne` is the simplest way
        // to return the authoritative post-upsert state. Performance impact is
        // negligible compared to the file upload I/O this sits behind.
        const current = await SkillFile.findOne({
            skillId: row.skillId,
            relativePath: row.relativePath,
        }).lean();
        return current;
    }
    async function deleteSkillFile(skillId, relativePath) {
        const SkillFile = mongoose.models.SkillFile;
        const res = await SkillFile.deleteOne({ skillId, relativePath });
        if (!res.deletedCount) {
            return { deleted: false };
        }
        await bumpSkillVersionAndAdjustFileCount(skillId, -1);
        return { deleted: true };
    }
    // The public surface is scoped to methods that handlers and the user
    async function getSkillFileByPath(skillId, relativePath) {
        const SkillFile = mongoose.models.SkillFile;
        const row = await SkillFile.findOne({ skillId, relativePath }).lean();
        return row;
    }
    async function updateSkillFileContent(skillId, relativePath, update) {
        const SkillFile = mongoose.models.SkillFile;
        await SkillFile.updateOne({ skillId, relativePath }, { $set: update });
    }
    async function updateSkillFileCodeEnvIds(updates) {
        if (updates.length === 0)
            return { matchedCount: 0, modifiedCount: 0 };
        const SkillFile = mongoose.models.SkillFile;
        const ops = updates.map((u) => ({
            updateOne: {
                filter: { skillId: u.skillId, relativePath: u.relativePath },
                update: { $set: { codeEnvRef: u.codeEnvRef } },
            },
        }));
        /**
         * The returned `{matchedCount, modifiedCount}` lets callers warn on
         * partial writes — a silent miss here turns every subsequent prime
         * into a fresh upload (massive egress at scale). If the wrapper's
         * tenant injection ends up dropping rows, the warn log makes it
         * visible instead of failing closed.
         */
        const result = await tenantSafeBulkWrite(SkillFile, ops);
        if (result.modifiedCount < updates.length) {
            logger.warn(`[updateSkillFileCodeEnvIds] Persisted ${result.modifiedCount}/${updates.length} codeEnvRefs (matched ${result.matchedCount}). Subsequent primes for unmatched files will re-upload.`);
        }
        return { matchedCount: result.matchedCount, modifiedCount: result.modifiedCount };
    }
    return {
        createSkill,
        getSkillById,
        getSkillByName,
        listSkillsByAccess,
        listAlwaysApplySkills,
        updateSkill,
        deleteSkill,
        deleteUserSkills,
        listSkillFiles,
        upsertSkillFile,
        deleteSkillFile,
        getSkillFileByPath,
        updateSkillFileContent,
        updateSkillFileCodeEnvIds,
    };
}

export { backfillDerivedFromFrontmatter, createSkillMethods, deriveStructuredFrontmatterFields, inferSkillFileCategory, partitionIssues, validateAlwaysApply, validateRelativePath, validateSkillBody, validateSkillDescription, validateSkillDisplayTitle, validateSkillFrontmatter, validateSkillName };
//# sourceMappingURL=skill.es.js.map
