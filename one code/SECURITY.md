# Security Policy

## Supported Versions

Security support currently applies to the active development branch until the
first public release.

## Reporting A Vulnerability

Report vulnerabilities privately to the project maintainer.

Do not file public issues for vulnerabilities that could expose local files,
credentials, model provider keys, or workspace data.

## Current Security Boundary

OneCode uses path guards, verifier allowlists, and a Docker sandbox adapter.
The adapter is available as a v0.2 hardening foundation; production use still
requires explicit wiring, runtime policy, and deployment review.
