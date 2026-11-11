# OneCode Architecture

This document provides visual architecture diagrams to complement the textual design documents.

## System Overview

```mermaid
graph TB
    User[User/LibreChat] --> CLI[CLI Commands]
    User --> WebAPI[Web API :19080]
    
    CLI --> Runner[Runner/Orchestrator]
    WebAPI --> Runner
    
    Runner --> IChingKernel[I Ching Kernel]
    Runner --> PathGuard[Path Guard]
    Runner --> Checkpoint[Checkpoint Manager]
    
    IChingKernel --> StatusCode[6-bit Status Code<br/>0-63 Hexagrams]
    IChingKernel --> Transition[Transition Decision]
    
    PathGuard --> Workspace[Workspace Files]
    Checkpoint --> WAL[Write-Ahead Log]
    Checkpoint --> Manifest[Evidence Manifest]
    
    Transition --> Continue[Continue]
    Transition --> Halt[Halt]
    Transition --> Cooldown[Cooldown]
    Transition --> Discover[Discover]
    
    Runner --> Sandbox[Docker Sandbox<br/>Optional]
    
    style IChingKernel fill:#e1f5ff
    style PathGuard fill:#ffe1e1
    style Checkpoint fill:#e1ffe1
```

## I Ching State Machine

### Hexagram Structure

```
Status Code 40 = 0b101000 = Binary representation

Bit position:  5 4 3 | 2 1 0
Binary value:  1 0 1 | 0 0 0
               ─────   ─────
               Outer   Inner
               Trigram Trigram
                 |       |
                Li      Kun
              (Fire)  (Earth)
```

### State Transition Flow

```mermaid
stateDiagram-v2
    [*] --> EvaluateTask
    
    EvaluateTask --> CheckSafety: Encode 6-bit status
    
    CheckSafety --> Halt: Path breach<br/>Timeout<br/>Security violation
    CheckSafety --> AnalyzeBalance: Safety OK
    
    AnalyzeBalance --> Cooldown: Pure yang<br/>(6 yang lines)
    AnalyzeBalance --> Discover: Pure yin<br/>(0 yang lines)
    AnalyzeBalance --> CheckElements: Balanced<br/>(3-4 yang lines)
    
    CheckElements --> ElementRelation[Evaluate<br/>Five-Element Relation]
    
    ElementRelation --> Continue: Generation cycle<br/>(outer generates inner)
    ElementRelation --> Halt: Control cycle<br/>(outer controls inner)
    ElementRelation --> Checkpoint: Special relations
    
    Cooldown --> [*]
    Halt --> [*]
    Continue --> [*]
    Discover --> [*]
    Checkpoint --> [*]
```

## Five-Element Relations

### Element Cycles

```mermaid
graph LR
    subgraph "Generation Cycle (Accelerate/Continue)"
        Wood1[Wood 木] -->|generates| Fire1[Fire 火]
        Fire1 -->|generates| Earth1[Earth 土]
        Earth1 -->|generates| Metal1[Metal 金]
        Metal1 -->|generates| Water1[Water 水]
        Water1 -->|generates| Wood1
    end
    
    style Wood1 fill:#90EE90
    style Fire1 fill:#FFB6C1
    style Earth1 fill:#DEB887
    style Metal1 fill:#D3D3D3
    style Water1 fill:#ADD8E6
```

```mermaid
graph LR
    subgraph "Control Cycle (Halt/Throttle/Prune)"
        Wood2[Wood 木] -.->|controls| Earth2[Earth 土]
        Earth2 -.->|controls| Water2[Water 水]
        Water2 -.->|controls| Fire2[Fire 火]
        Fire2 -.->|controls| Metal2[Metal 金]
        Metal2 -.->|controls| Wood2
    end
    
    style Wood2 fill:#90EE90
    style Fire2 fill:#FFB6C1
    style Earth2 fill:#DEB887
    style Metal2 fill:#D3D3D3
    style Water2 fill:#ADD8E6
```

### Trigram to Element Mapping

| Trigram | Chinese | Binary | Element | Attributes |
|---------|---------|--------|---------|------------|
| Qian 乾 | ☰ | 111 | Metal | Creative, strong, heaven |
| Dui 兑  | ☱ | 110 | Metal | Joyful, lake |
| Li 离   | ☲ | 101 | Fire  | Radiant, clarity, fire |
| Zhen 震 | ☳ | 100 | Wood  | Arousing, thunder |
| Xun 巽  | ☴ | 011 | Wood  | Gentle, wind |
| Kan 坎  | ☵ | 010 | Water | Abysmal, water |
| Gen 艮  | ☶ | 001 | Earth | Keeping still, mountain |
| Kun 坤  | ☷ | 000 | Earth | Receptive, earth |

## Decision Priority Hierarchy

```mermaid
graph TD
    Start[Task Execution Request] --> Encode[Encode to 6-bit status code]
    
    Encode --> P1{Priority 1:<br/>Hard Safety?}
    
    P1 -->|Path breach| HaltSafety[HALT:<br/>sovereignty_breach]
    P1 -->|Timeout| HaltTimeout[HALT:<br/>timeout]
    P1 -->|Security| HaltSec[HALT:<br/>security_violation]
    
    P1 -->|Safe| P2{Priority 2:<br/>Yin-Yang Pressure?}
    
    P2 -->|6 yang lines| Cooldown[COOLDOWN:<br/>yang_overload]
    P2 -->|0 yang lines| Discover[DISCOVER:<br/>yin_deficiency]
    
    P2 -->|Balanced| P3{Priority 3:<br/>Five-Element<br/>Relation?}
    
    P3 -->|Outer generates inner| Continue[CONTINUE:<br/>generation_support]
    P3 -->|Outer controls inner| HaltControl[HALT:<br/>control_conflict]
    P3 -->|Special case| Checkpoint[CHECKPOINT:<br/>preserve_state]
    
    P3 -->|No relation| P4[Priority 4:<br/>Neutral Fallback]
    
    P4 --> Discover2[DISCOVER or CONTINUE]
    
    style P1 fill:#ff6b6b
    style P2 fill:#ffd93d
    style P3 fill:#6bcf7f
    style P4 fill:#95a5a6
```

## Execution Flow with Evidence Chain

```mermaid
sequenceDiagram
    participant User
    participant Runner
    participant Kernel as I Ching Kernel
    participant Guard as Path Guard
    participant WAL
    participant Workspace
    
    User->>Runner: Execute task
    Runner->>Kernel: Evaluate state (6-bit code)
    Kernel-->>Runner: Transition decision
    
    alt Decision: Continue
        Runner->>Guard: Check path validity
        Guard-->>Runner: Path OK
        Runner->>WAL: Append intention
        Runner->>Workspace: Write file (atomic)
        WAL->>WAL: Record completion
        Runner-->>User: Task completed
    else Decision: Halt
        Runner->>WAL: Append halt reason
        Runner-->>User: Task halted (with reason)
    else Decision: Cooldown
        Runner->>WAL: Append cooldown event
        Runner-->>User: Cooldown period
    end
```

## Path Guard Security Model

```mermaid
graph TB
    Request[File Write Request] --> Parse[Parse requested path]
    
    Parse --> Resolve[Path.resolve<br/>Canonicalize path]
    Resolve --> Check{Inside<br/>workspace?}
    
    Check -->|No| Reject1[❌ REJECT:<br/>Path traversal]
    Check -->|Yes| Blacklist{In blacklist?}
    
    Blacklist -->|.git/*| Reject2[❌ REJECT:<br/>Version control]
    Blacklist -->|.github/*| Reject3[❌ REJECT:<br/>CI/CD config]
    Blacklist -->|pyproject.toml| Reject4[❌ REJECT:<br/>Root config]
    Blacklist -->|.env| Reject5[❌ REJECT:<br/>Secrets]
    
    Blacklist -->|Safe| DirCheck{Parent dir<br/>exists?}
    
    DirCheck -->|No| Reject6[❌ REJECT:<br/>Invalid parent]
    DirCheck -->|Yes| Atomic[Atomic write:<br/>temp → fsync → replace]
    
    Atomic --> WAL[Record in WAL]
    WAL --> Success[✅ Write successful]
    
    style Reject1 fill:#ff6b6b
    style Reject2 fill:#ff6b6b
    style Reject3 fill:#ff6b6b
    style Reject4 fill:#ff6b6b
    style Reject5 fill:#ff6b6b
    style Reject6 fill:#ff6b6b
    style Success fill:#51cf66
```

## Docker Sandbox Isolation

```mermaid
graph LR
    subgraph Host System
        Runner[OneCode Runner]
    end
    
    subgraph Docker Container
        subgraph Restrictions
            NoNet[❌ Network disabled<br/>--network=none]
            NoCap[❌ All capabilities dropped<br/>--cap-drop=ALL]
            ReadOnly[❌ Root filesystem read-only<br/>--read-only]
            Limited[⚠️ Memory: 512MB<br/>⚠️ CPUs: 1<br/>⚠️ PIDs: 256]
        end
        
        Exec[Command Execution<br/>shell=False]
        TmpFS[/tmp tmpfs<br/>noexec, nosuid, 64MB]
        Mount[Workspace mount<br/>read-write]
    end
    
    Runner -->|Execute| Exec
    Exec --> Mount
    
    style NoNet fill:#ff6b6b
    style NoCap fill:#ff6b6b
    style ReadOnly fill:#ff6b6b
    style Limited fill:#ffd93d
    style Mount fill:#51cf66
```

## Common Status Code Examples

| Code | Binary | Outer/Inner | Elements | Relation | Typical Decision | Reason |
|------|--------|-------------|----------|----------|------------------|--------|
| 0 | 000000 | Kun/Kun | Earth/Earth | Same | Discover | Pure yin, rule gap |
| 17 | 010001 | Kan/Gen | Water/Earth | Control | Checkpoint | Water over earth, preserve |
| 35 | 100011 | Zhen/Xun | Wood/Wood | Same | Cooldown | High yang, throttle |
| 39 | 100111 | Zhen/Qian | Wood/Metal | Control | Cooldown | Yang overload |
| 40 | 101000 | Li/Kun | Fire/Earth | Control | Halt | Sovereignty breach |
| 49 | 110001 | Dui/Gen | Metal/Earth | Generate | Continue | Generation support |
| 63 | 111111 | Qian/Qian | Metal/Metal | Same | Cooldown | Pure yang, maximum |

## Module Dependencies

```mermaid
graph TB
    subgraph "CLI Layer"
        CLI[cli_commands/]
    end
    
    subgraph "API Layer"
        Web[web/api.py]
        TUI[tui/app.py]
    end
    
    subgraph "Core Kernel"
        Hex[kernel/hexagram.py<br/>I Ching Rules]
        Runner[kernel/runner.py<br/>Orchestrator]
        Model[kernel/model_loop.py<br/>LLM Integration]
        Guard[kernel/path_guard.py<br/>Security]
        Check[kernel/checkpoint.py<br/>State Management]
        Exec[kernel/execution_tools.py<br/>Command Runner]
        Sand[kernel/sandbox.py<br/>Docker Isolation]
    end
    
    CLI --> Runner
    Web --> Runner
    TUI --> Runner
    
    Runner --> Hex
    Runner --> Guard
    Runner --> Check
    Runner --> Model
    
    Model --> Exec
    Exec --> Sand
    Check --> Exec
    
    style Hex fill:#e1f5ff
    style Guard fill:#ffe1e1
    style Check fill:#e1ffe1
```

## Data Flow: Task Execution

```mermaid
flowchart LR
    Input[Task Input] --> Parse[Parse Specification]
    Parse --> Context[Load Context:<br/>Project rules<br/>Skills<br/>Runtime config]
    
    Context --> Encode[Encode State<br/>6-bit status code]
    Encode --> Kernel[I Ching Kernel<br/>Decide transition]
    
    Kernel --> Decision{Decision?}
    
    Decision -->|Continue| PathCheck[Path Guard Check]
    Decision -->|Halt| Evidence1[Append to WAL]
    Decision -->|Cooldown| Evidence2[Append to WAL]
    
    PathCheck --> Valid{Valid?}
    Valid -->|Yes| Execute[Execute Action]
    Valid -->|No| Breach[Record Breach]
    
    Execute --> Record[Record to WAL]
    Execute --> Asset[Write Asset]
    
    Record --> Manifest[Update Manifest]
    Breach --> Evidence3[Append to WAL]
    Evidence1 --> Output
    Evidence2 --> Output
    Evidence3 --> Output
    Manifest --> Output[Return Evidence]
    
    style Kernel fill:#e1f5ff
    style PathCheck fill:#ffe1e1
    style Record fill:#e1ffe1
```

---

## Additional Resources

- [I Ching Complete Rule Kernel Design](superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md) - Mathematical foundations
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Required reading for developers
- [INDEX.md](INDEX.md) - Full documentation index

For interactive exploration:
```bash
onecode doctor           # Run smoke tests with status code examples
onecode math-audit       # Verify state space integrity
onecode inspect --run-id <id>  # View hexagram details for a specific run
```
