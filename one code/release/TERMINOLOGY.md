# Public Terminology Guide

Public release copy should use neutral engineering terminology.

The local development tree may keep historical research names and internal
symbolic model references. Do not copy those names into public landing pages,
package summaries, marketplace listings, or integration briefs unless the
audience explicitly asks for the research background.

## Preferred Terms

| Public term | Meaning |
| --- | --- |
| deterministic state profile | Machine-readable state record attached to a run. |
| 6-bit state code | Compact state code used by the kernel transition surface. |
| transition rule | Deterministic mapping from one state profile to the next decision. |
| binary state bit | A single active/inactive state component. |
| 2-bit window | Adjacent two-bit local state window. |
| 3-bit plane | Lower or upper three-bit state projection. |
| state relation graph | Cyclic or relational rule graph used for scheduling/audit decisions. |
| shell projection | Stable UI/API-facing view over raw kernel evidence. |
| WAL evidence | Append-only run evidence stream. |
| hash-chain validation | Tamper-evident validation over WAL records. |
| guarded write | File mutation allowed only after intent, path, and evidence checks. |
| forensic fallback | Stronger evidence mode used for denied or halted execution paths. |

## Terms To Avoid In Public Release Copy

Avoid internal symbolic or cultural research terms in public release materials.
Describe the project with state-machine, transition, evidence, audit, and
guardrail language instead.

Internal symbolic terms may remain in local development files, internal docs,
tests, legacy field names, and compatibility code. The public release pack does
not rename the implementation or remove backward compatibility.

## Compatibility Boundary

Some raw evidence fields and internal APIs may still contain legacy names for
backward compatibility. Public adapters should prefer `shell_projection` and
user-facing labels such as:

- `state_code`
- `transition_action`
- `transition_reason`
- `dispatch_decision`
- `evidence_ref`
- `resume_state`

If a public integration needs a new stable field name, add it as an alias rather
than removing the existing internal field.
