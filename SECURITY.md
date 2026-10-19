# Security Policy

## Supported Versions

Security support currently applies to the active development branch until the
first public release.

## Reporting A Vulnerability

Report vulnerabilities privately to the project maintainer.

Do not file public issues for vulnerabilities that could expose local files,
credentials, model provider keys, or workspace data.

## Current Security Boundary

OneCode is a local kernel. These controls are enforced in the current tree:

- workspace path checks reject traversal, case-variant sensitive paths, symlinks, and `.onecode/` writes
- model-planned writes and commands on the web resume path require explicit approval
- approval plans are authenticated with a private HMAC key under `ONECODE_HOME`
- verifier commands cannot impersonate Python by path, and verifier processes do not inherit API keys
- local HTTP requests must target the loopback listener; non-JSON content types are rejected
- changing a model endpoint's host does not reuse the stored API key
- shell startup rejects the published passwords `dev-local-token` and `OneCode123!`

`onecode doctor` reports this boundary in the `deployment_boundary` check.
`production_ready` is true only when Docker is available for command execution,
`ONECODE_ALLOW_UNAUTHENTICATED` is off, and an API token is set. When
`ONECODE_API_TOKEN` is unset, a mode `0600` file at `$ONECODE_HOME/shell/api-token`
supplies that token. An empty environment value does not, and a file that allows
group or world access does not count.
Without Docker, `run_command` stays on the host. That mode is for a trusted local workspace, not for untrusted repositories or a network-facing deployment.
