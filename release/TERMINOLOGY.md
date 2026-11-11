# Public Terminology Guide / 公开术语指南

Public release copy should use neutral engineering terminology.

公开发布文案应使用中性的工程术语。

The local development tree may keep historical research names and internal
symbolic model references. Do not copy those names into public landing pages,
package summaries, marketplace listings, or integration briefs unless the
audience explicitly asks for the research background.

本地开发树可以保留历史研究命名和内部符号模型引用。除非受众明确要求了解研究背景，否则不要把这些名称复制到公开落地页、包摘要、市场列表或集成说明中。

## Preferred Terms / 推荐术语

| Public term / 公开术语 | Meaning / 含义 |
| --- | --- |
| deterministic state profile / 确定性状态画像 | Machine-readable state record attached to a run. / 附着在一次运行上的机器可读状态记录。 |
| 6-bit state code / 6-bit 状态码 | Compact state code used by the kernel transition surface. / 内核状态转移面使用的紧凑状态码。 |
| transition rule / 状态转移规则 | Deterministic mapping from one state profile to the next decision. / 从状态画像到下一步决策的确定性映射。 |
| binary state bit / 二值状态位 | A single active/inactive state component. / 单个激活或未激活状态组件。 |
| 2-bit window / 2-bit 窗口 | Adjacent two-bit local state window. / 相邻两位构成的局部状态窗口。 |
| 3-bit plane / 3-bit 平面 | Lower or upper three-bit state projection. / 低三位或高三位状态投影。 |
| state relation graph / 状态关系图 | Cyclic or relational rule graph used for scheduling/audit decisions. / 用于调度或审计决策的循环或关系规则图。 |
| shell projection / 壳层投影 | Stable UI/API-facing view over raw kernel evidence. / 面向 UI/API 的稳定视图，封装原始内核证据。 |
| WAL evidence / WAL 证据 | Append-only run evidence stream. / 追加式运行证据流。 |
| hash-chain validation / 哈希链校验 | Tamper-evident validation over WAL records. / 对 WAL 记录进行防篡改校验。 |
| guarded write / 受保护写入 | File mutation allowed only after intent, path, and evidence checks. / 只有通过意图、路径和证据检查后才允许文件变更。 |
| forensic fallback / 取证回退 | Stronger evidence mode used for denied or halted execution paths. / 拒绝或中止路径使用的更强证据模式。 |

## Terms To Avoid In Public Release Copy / 公开文案避免项

Avoid internal symbolic or cultural research terms in public release materials.
Describe the project with state-machine, transition, evidence, audit, and
guardrail language instead.

公开发布材料应避免内部符号或文化研究术语。优先使用状态机、状态转移、证据、审计和安全护栏语言描述项目。

Internal symbolic terms may remain in local development files, internal docs,
tests, legacy field names, and compatibility code. The public release pack does
not rename the implementation or remove backward compatibility.

内部符号术语可以保留在本地开发文件、内部文档、测试、历史字段名和兼容代码中。公开发布包不重命名实现，也不移除向后兼容性。

## Compatibility Boundary / 兼容边界

Some raw evidence fields and internal APIs may still contain legacy names for
backward compatibility. Public adapters should prefer `shell_projection` and
user-facing labels such as:

部分原始证据字段和内部 API 可能仍因向后兼容保留历史名称。公开适配器应优先使用 `shell_projection` 和以下面向用户的标签：

- `state_code`
- `transition_action`
- `transition_reason`
- `dispatch_decision`
- `evidence_ref`
- `resume_state`

If a public integration needs a new stable field name, add it as an alias rather
than removing the existing internal field.

如果公开集成需要新的稳定字段名，应添加别名，而不是删除既有内部字段。

