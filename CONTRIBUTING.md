# Contributing

Run verification before submitting changes:

```bash
bash scripts/verify.sh
```

Keep OneCode core changes separate from LibreChat shell changes.

Do not introduce gateway dependencies into the OneCode shell line.

Do not commit generated local run data, temporary workspaces, private keys, or
provider credentials.

## Source Hygiene

Leaked, mirrored, or DMCA-risk Claude Code source repositories are forbidden as
inputs to this project.

Every OneCode source file must be independently authored or come from a clearly
licensed dependency, fixture, or reference that is safe to redistribute.
