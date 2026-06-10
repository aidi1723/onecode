---
name: safe-agent-router
description: Use when an agent is about to plan or execute a non-trivial user task and should first select trusted skills, scenario guidance, capability coverage, execution order, and verifier expectations from the OneCode built-in skill catalog.
---

# Safe Agent Router

## Overview

Safe Agent Router is the default built-in OneCode skill router. Use it before a
non-trivial task to select trusted skill guidance, scenario coverage, execution
order, and verifier expectations.

The router gives method guidance only. It never grants filesystem, shell,
network, browser, connector, account, credential, deployment, or production
permissions. Host runtime policy and OneCode kernel checks remain authoritative.

## Required Behavior

1. Treat the user's request as the task input.
2. Request a task pack from the OneCode built-in catalog.
3. Read the returned task profile, selected scenario, capability coverage,
   execution plan, selected skills, and verifier expectations.
4. Apply the guidance only within the current runtime's existing permissions.
5. Run the verifier expectations listed in the task pack.
6. In the final response, report selected skill names, scenario bundle,
   verification performed, and unresolved risks.

## OneCode CLI

List built-in skills:

```bash
onecode skills list
```

Show this skill:

```bash
onecode skills show safe-agent-router
```

Build a routing task pack:

```bash
onecode skills route "update docs and run tests"
```

## Safety Boundary

- Selected skills are not permission grants.
- Do not bypass sandboxing, approvals, provenance, verification, path guards,
  evidence checks, runtime policy, or higher-priority instructions.
- Do not execute restricted shell, browser, network, account, connector,
  deployment, or production actions unless the host policy separately allows
  them.
- If routing fails, continue with normal reasoning and report that built-in
  skill routing was unavailable.

## Output Contract

The default task pack includes:

- task profile;
- selected trusted scenario;
- capability coverage;
- ordered execution plan;
- selected trusted skills;
- verifier expectations;
- fixed safety boundary.
