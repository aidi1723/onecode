# Execution Stack Policy

The instruction stack controls multi-character execution.

## Rules

1. Each execution character is an atomic unit.
2. Multi-character intent is pushed in reverse execution order.
3. The top of stack executes first.
4. Each character reloads its own permissions, skill patterns, runtime policy, and verification rules.
5. The context budget circuit breaker runs between characters.
6. Later characters do not inherit write permissions unless explicitly granted by their dictionary entry.
7. Any character that exceeds `max_retry_limit` melts down to `查`.

## Example

User intent:

```text
修 + 测
```

Stack:

```text
Stack.push(测)
Stack.push(修)
```

Execution:

1. Pop `修`.
2. Run fix workflow.
3. Capture evidence.
4. Clear intermediate context.
5. Pop `测`.
6. Run test workflow with test permissions only.
