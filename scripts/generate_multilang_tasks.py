#!/usr/bin/env python3
"""Generate Go, TypeScript, and Rust benchmark task suites for OneCode.

Creates 10 tasks for each language in benchmarks/tasks/{golang,typescript,rust}.
Pure standard-library only.
"""
from __future__ import annotations

import json
from pathlib import Path


def generate_golang_tasks(base_dir: Path) -> list[str]:
    tasks_dir = base_dir / "golang"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    created = []

    tasks = [
        {
            "id": "go-01-module-init",
            "prompt": "初始化 Go 模块 example.com/service",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "go.mod",
                            "content": "module example.com/service\n\ngo 1.22\n",
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "go.mod", "text": "module example.com/service"},
                {"type": "file_contains", "path": "go.mod", "text": "go 1.22"},
            ],
        },
        {
            "id": "go-02-http-handler",
            "prompt": "编写 net/http 基础健康检查处理器",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "cmd/server/main.go",
                            "content": (
                                "package main\n\nimport (\n\t\"fmt\"\n\t\"net/http\"\n)\n\n"
                                "func healthHandler(w http.ResponseWriter, r *http.Request) {\n"
                                "\tw.WriteHeader(http.StatusOK)\n\tfmt.Fprintln(w, `{\"status\":\"ok\"}`)\n"
                                "}\n\nfunc main() {\n\thttp.HandleFunc(\"/health\", healthHandler)\n}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "cmd/server/main.go", "text": "http.HandleFunc(\"/health\""},
                {"type": "file_contains", "path": "cmd/server/main.go", "text": "{\"status\":\"ok\"}"},
            ],
        },
        {
            "id": "go-03-struct-json",
            "prompt": "定义用户数据结构并标注 JSON 标签",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "pkg/models/user.go",
                            "content": (
                                "package models\n\ntype User struct {\n"
                                "\tID        int64  `json:\"id\"`\n"
                                "\tUsername  string `json:\"username\"`\n"
                                "\tEmail     string `json:\"email,omitempty\"`\n"
                                "\tIsActive  bool   `json:\"is_active\"`\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/models/user.go", "text": "`json:\"id\"`"},
                {"type": "file_contains", "path": "pkg/models/user.go", "text": "`json:\"username\"`"},
            ],
        },
        {
            "id": "go-04-error-handling",
            "prompt": "实现带有 Error() 方法的自定义领域错误",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "pkg/errors/sentinel.go",
                            "content": (
                                "package errors\n\nimport \"errors\"\n\n"
                                "var ErrNotFound = errors.New(\"resource not found\")\n\n"
                                "type DomainError struct {\n\tCode    string\n\tMessage string\n}\n\n"
                                "func (e *DomainError) Error() string {\n\treturn e.Code + \": \" + e.Message\n}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/errors/sentinel.go", "text": "ErrNotFound = errors.New"},
                {"type": "file_contains", "path": "pkg/errors/sentinel.go", "text": "func (e *DomainError) Error()"},
            ],
        },
        {
            "id": "go-05-patch-concurrency",
            "prompt": "为并发安全缓存补充 sync.RWMutex 读写锁",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [
                    {
                        "path": "pkg/cache/cache.go",
                        "content": (
                            "package cache\n\nimport \"sync\"\n\ntype Cache struct {\n"
                            "\tmu    sync.RWMutex\n\titems map[string]string\n}\n\n"
                            "func (c *Cache) Set(k, v string) {\n\tc.items[k] = v\n}\n"
                        ),
                    }
                ],
                "script": [
                    {
                        "tool_name": "patch_text",
                        "params": {
                            "path": "pkg/cache/cache.go",
                            "search_block": "func (c *Cache) Set(k, v string) {\n\tc.items[k] = v\n}",
                            "replace_block": (
                                "func (c *Cache) Set(k, v string) {\n"
                                "\tc.mu.Lock()\n\tdefer c.mu.Unlock()\n\tc.items[k] = v\n}"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/cache/cache.go", "text": "c.mu.Lock()"},
                {"type": "file_contains", "path": "pkg/cache/cache.go", "text": "defer c.mu.Unlock()"},
            ],
        },
        {
            "id": "go-06-interface-contract",
            "prompt": "声明 Store 存储接口及其内存实现",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "pkg/store/store.go",
                            "content": (
                                "package store\n\ntype Store interface {\n"
                                "\tGet(key string) (string, error)\n\tPut(key, val string) error\n}\n\n"
                                "type MemoryStore struct {\n\tdata map[string]string\n}\n\n"
                                "func NewMemoryStore() *MemoryStore {\n"
                                "\treturn &MemoryStore{data: make(map[string]string)}\n}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/store/store.go", "text": "type Store interface"},
                {"type": "file_contains", "path": "pkg/store/store.go", "text": "func NewMemoryStore()"},
            ],
        },
        {
            "id": "go-07-unit-test",
            "prompt": "编写计算模块的标准测试用例",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [
                    {
                        "path": "pkg/calc/calc.go",
                        "content": "package calc\n\nfunc Add(a, b int) int {\n\treturn a + b\n}\n",
                    }
                ],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "pkg/calc/calc_test.go",
                            "content": (
                                "package calc\n\nimport \"testing\"\n\n"
                                "func TestAdd(t *testing.T) {\n"
                                "\tif got := Add(2, 3); got != 5 {\n"
                                "\t\tt.Errorf(\"expected 5, got %d\", got)\n\t}\n}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/calc/calc_test.go", "text": "func TestAdd(t *testing.T)"},
                {"type": "file_contains", "path": "pkg/calc/calc_test.go", "text": "t.Errorf"},
            ],
        },
        {
            "id": "go-08-context-timeout",
            "prompt": "通过 context.WithTimeout 设定请求超时",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [
                    {
                        "path": "pkg/client/client.go",
                        "content": (
                            "package client\n\nimport \"context\"\n\n"
                            "func Fetch(ctx context.Context) error {\n\treturn nil\n}\n"
                        ),
                    }
                ],
                "script": [
                    {
                        "tool_name": "patch_text",
                        "params": {
                            "path": "pkg/client/client.go",
                            "search_block": "func Fetch(ctx context.Context) error {\n\treturn nil\n}",
                            "replace_block": (
                                "import \"time\"\n\nfunc Fetch(parent context.Context) error {\n"
                                "\tctx, cancel := context.WithTimeout(parent, 5*time.Second)\n"
                                "\tdefer cancel()\n\t_ = ctx\n\treturn nil\n}"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/client/client.go", "text": "context.WithTimeout"},
                {"type": "file_contains", "path": "pkg/client/client.go", "text": "defer cancel()"},
            ],
        },
        {
            "id": "go-09-middleware-chain",
            "prompt": "实现标准 HTTP 日志与中间件包装器",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "pkg/middleware/chain.go",
                            "content": (
                                "package middleware\n\nimport (\n\t\"log\"\n\t\"net/http\"\n)\n\n"
                                "func LoggingMiddleware(next http.Handler) http.Handler {\n"
                                "\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {\n"
                                "\t\tlog.Printf(\"%s %s\", r.Method, r.URL.Path)\n"
                                "\t\tnext.ServeHTTP(w, r)\n\t})\n}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/middleware/chain.go", "text": "func LoggingMiddleware"},
                {"type": "file_contains", "path": "pkg/middleware/chain.go", "text": "next.ServeHTTP"},
            ],
        },
        {
            "id": "go-10-graceful-shutdown",
            "prompt": "配置系统信号监听并执行 HTTP 服务优雅退出",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "pkg/server/graceful.go",
                            "content": (
                                "package server\n\nimport (\n\t\"context\"\n\t\"net/http\"\n"
                                "\t\"os\"\n\t\"os/signal\"\n\t\"syscall\"\n\t\"time\"\n)\n\n"
                                "func ShutdownServer(srv *http.Server) error {\n"
                                "\tquit := make(chan os.Signal, 1)\n"
                                "\tsignal.Notify(quit, os.Interrupt, syscall.SIGTERM)\n"
                                "\t<-quit\n"
                                "\tctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)\n"
                                "\tdefer cancel()\n"
                                "\treturn srv.Shutdown(ctx)\n}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "pkg/server/graceful.go", "text": "signal.Notify"},
                {"type": "file_contains", "path": "pkg/server/graceful.go", "text": "srv.Shutdown(ctx)"},
            ],
        },
    ]

    for task in tasks:
        path = tasks_dir / f"{task['id']}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(str(path))
    return created


def generate_typescript_tasks(base_dir: Path) -> list[str]:
    tasks_dir = base_dir / "typescript"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    created = []

    tasks = [
        {
            "id": "ts-01-package-json",
            "prompt": "创建 TypeScript 项目 package.json 声明 ESM 模块",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "package.json",
                            "content": json.dumps(
                                {
                                    "name": "@onecode/typed-service",
                                    "version": "1.0.0",
                                    "type": "module",
                                    "scripts": {
                                        "build": "tsc -b",
                                        "test": "vitest run",
                                    },
                                },
                                indent=2,
                            )
                            + "\n",
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "package.json", "text": '"type": "module"'},
                {"type": "file_contains", "path": "package.json", "text": '"@onecode/typed-service"'},
            ],
        },
        {
            "id": "ts-02-tsconfig",
            "prompt": "创建 tsconfig.json 开启严格类型检查",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "tsconfig.json",
                            "content": json.dumps(
                                {
                                    "compilerOptions": {
                                        "target": "ES2022",
                                        "module": "NodeNext",
                                        "moduleResolution": "NodeNext",
                                        "strict": True,
                                        "noImplicitAny": True,
                                        "skipLibCheck": True,
                                    },
                                    "include": ["src/**/*"],
                                },
                                indent=2,
                            )
                            + "\n",
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "tsconfig.json", "text": '"strict": true'},
                {"type": "file_contains", "path": "tsconfig.json", "text": '"moduleResolution": "NodeNext"'},
            ],
        },
        {
            "id": "ts-03-interface-guard",
            "prompt": "定义接口与自定义类型收窄守卫",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/guard.ts",
                            "content": (
                                "export interface UserAccount {\n"
                                "  id: string;\n"
                                "  role: 'admin' | 'operator' | 'viewer';\n"
                                "}\n\n"
                                "export function isUserAccount(val: unknown): val is UserAccount {\n"
                                "  return typeof val === 'object' && val !== null && 'id' in val && 'role' in val;\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/guard.ts", "text": "val is UserAccount"},
                {"type": "file_contains", "path": "src/guard.ts", "text": "export interface UserAccount"},
            ],
        },
        {
            "id": "ts-04-generic-result",
            "prompt": "实现泛型 Result 联合类型与其构造器",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/result.ts",
                            "content": (
                                "export type Result<T, E = Error> =\n"
                                "  | { ok: true; value: T }\n"
                                "  | { ok: false; error: E };\n\n"
                                "export function ok<T>(value: T): Result<T, never> {\n"
                                "  return { ok: true, value };\n"
                                "}\n\n"
                                "export function err<E>(error: E): Result<never, E> {\n"
                                "  return { ok: false, error };\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/result.ts", "text": "export type Result<T, E = Error>"},
                {"type": "file_contains", "path": "src/result.ts", "text": "export function ok<T>"},
            ],
        },
        {
            "id": "ts-05-async-retry",
            "prompt": "编写带有指数退避的异步重试工具函数",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/retry.ts",
                            "content": (
                                "export async function retry<T>(\n"
                                "  operation: () => Promise<T>,\n"
                                "  maxAttempts: number = 3,\n"
                                "  baseDelayMs: number = 100\n"
                                "): Promise<T> {\n"
                                "  for (let attempt = 1; attempt <= maxAttempts; attempt++) {\n"
                                "    try {\n"
                                "      return await operation();\n"
                                "    } catch (err) {\n"
                                "      if (attempt === maxAttempts) throw err;\n"
                                "      await new Promise(r => setTimeout(r, baseDelayMs * Math.pow(2, attempt - 1)));\n"
                                "    }\n"
                                "  }\n"
                                "  throw new Error('unreachable');\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/retry.ts", "text": "export async function retry<T>"},
                {"type": "file_contains", "path": "src/retry.ts", "text": "baseDelayMs * Math.pow(2"},
            ],
        },
        {
            "id": "ts-06-patch-null-safety",
            "prompt": "修复深层对象访问潜在的 TypeError 异常",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [
                    {
                        "path": "src/profile.ts",
                        "content": (
                            "export function getEmail(user: any): string {\n"
                            "  return user.details.contact.email;\n"
                            "}\n"
                        ),
                    }
                ],
                "script": [
                    {
                        "tool_name": "patch_text",
                        "params": {
                            "path": "src/profile.ts",
                            "search_block": "  return user.details.contact.email;",
                            "replace_block": "  return user?.details?.contact?.email ?? 'anonymous@example.com';",
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/profile.ts", "text": "user?.details?.contact?.email ??"},
            ],
        },
        {
            "id": "ts-07-zod-schema",
            "prompt": "声明配置输入校验模式",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/schema.ts",
                            "content": (
                                "export interface AppConfig {\n"
                                "  port: number;\n"
                                "  host: string;\n"
                                "  debug?: boolean;\n"
                                "}\n\n"
                                "export function validateConfig(raw: unknown): AppConfig {\n"
                                "  if (typeof raw !== 'object' || raw === null) throw new Error('Invalid config object');\n"
                                "  const obj = raw as Record<string, unknown>;\n"
                                "  if (typeof obj.port !== 'number' || typeof obj.host !== 'string') throw new Error('Field mismatch');\n"
                                "  return { port: obj.port, host: obj.host, debug: Boolean(obj.debug) };\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/schema.ts", "text": "export interface AppConfig"},
                {"type": "file_contains", "path": "src/schema.ts", "text": "export function validateConfig"},
            ],
        },
        {
            "id": "ts-08-event-emitter",
            "prompt": "实现类型安全的泛型 EventEmitter 发布订阅器",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/emitter.ts",
                            "content": (
                                "export class TypedEmitter<EventMap extends Record<string, any>> {\n"
                                "  private listeners = new Map<keyof EventMap, Set<(data: any) => void>>();\n\n"
                                "  on<K extends keyof EventMap>(event: K, handler: (data: EventMap[K]) => void): void {\n"
                                "    if (!this.listeners.has(event)) this.listeners.set(event, new Set());\n"
                                "    this.listeners.get(event)!.add(handler);\n"
                                "  }\n\n"
                                "  emit<K extends keyof EventMap>(event: K, data: EventMap[K]): void {\n"
                                "    this.listeners.get(event)?.forEach(fn => fn(data));\n"
                                "  }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/emitter.ts", "text": "class TypedEmitter<EventMap"},
                {"type": "file_contains", "path": "src/emitter.ts", "text": "on<K extends keyof EventMap>"},
            ],
        },
        {
            "id": "ts-09-deep-readonly",
            "prompt": "编写递归 DeepReadonly 工具类型",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/readonly.ts",
                            "content": (
                                "export type DeepReadonly<T> = T extends (infer R)[]\n"
                                "  ? ReadonlyArray<DeepReadonly<R>>\n"
                                "  : T extends Function\n"
                                "  ? T\n"
                                "  : T extends object\n"
                                "  ? { readonly [K in keyof T]: DeepReadonly<T[K]> }\n"
                                "  : T;\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/readonly.ts", "text": "export type DeepReadonly<T>"},
                {"type": "file_contains", "path": "src/readonly.ts", "text": "readonly [K in keyof T]"},
            ],
        },
        {
            "id": "ts-10-vitest-spec",
            "prompt": "为计算器编写单元测试套件",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "tests/calc.spec.ts",
                            "content": (
                                "export function add(a: number, b: number): number { return a + b; }\n\n"
                                "export function testAddition() {\n"
                                "  if (add(2, 3) !== 5) throw new Error('Assertion failed: 2 + 3 != 5');\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "tests/calc.spec.ts", "text": "export function add"},
                {"type": "file_contains", "path": "tests/calc.spec.ts", "text": "Assertion failed"},
            ],
        },
    ]

    for task in tasks:
        path = tasks_dir / f"{task['id']}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(str(path))
    return created


def generate_rust_tasks(base_dir: Path) -> list[str]:
    tasks_dir = base_dir / "rust"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    created = []

    tasks = [
        {
            "id": "rs-01-cargo-toml",
            "prompt": "创建 Cargo.toml 清单文件并配置元数据",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "Cargo.toml",
                            "content": (
                                "[package]\n"
                                "name = \"onecode-core\"\n"
                                "version = \"0.1.0\"\n"
                                "edition = \"2021\"\n\n"
                                "[lib]\n"
                                "crate-type = [\"cdylib\", \"rlib\"]\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "Cargo.toml", "text": 'name = "onecode-core"'},
                {"type": "file_contains", "path": "Cargo.toml", "text": 'edition = "2021"'},
            ],
        },
        {
            "id": "rs-02-enum-result",
            "prompt": "定义领域错误枚举并派生 Debug 与 Display",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/error.rs",
                            "content": (
                                "use std::fmt;\n\n"
                                "#[derive(Debug)]\n"
                                "pub enum AppError {\n"
                                "    NotFound(String),\n"
                                "    Unauthorized,\n"
                                "}\n\n"
                                "impl fmt::Display for AppError {\n"
                                "    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {\n"
                                "        match self {\n"
                                "            AppError::NotFound(res) => write!(f, \"Resource not found: {}\", res),\n"
                                "            AppError::Unauthorized => write!(f, \"Unauthorized access\"),\n"
                                "        }\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/error.rs", "text": "pub enum AppError"},
                {"type": "file_contains", "path": "src/error.rs", "text": "impl fmt::Display for AppError"},
            ],
        },
        {
            "id": "rs-03-trait-definition",
            "prompt": "声明 Codec 序列化 Trait 接口",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/codec.rs",
                            "content": (
                                "pub trait Codec {\n"
                                "    fn encode(&self) -> Vec<u8>;\n"
                                "    fn decode(bytes: &[u8]) -> Result<Self, String> where Self: Sized;\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/codec.rs", "text": "pub trait Codec"},
                {"type": "file_contains", "path": "src/codec.rs", "text": "fn encode(&self)"},
            ],
        },
        {
            "id": "rs-04-struct-impl",
            "prompt": "实现带有关联函数与构建器模式的 Client 结构体",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/client.rs",
                            "content": (
                                "pub struct Client {\n"
                                "    endpoint: String,\n"
                                "    timeout_secs: u64,\n"
                                "}\n\n"
                                "impl Client {\n"
                                "    pub fn new(endpoint: &str) -> Self {\n"
                                "        Self { endpoint: endpoint.to_string(), timeout_secs: 30 }\n"
                                "    }\n"
                                "    pub fn with_timeout(mut self, secs: u64) -> Self {\n"
                                "        self.timeout_secs = secs;\n"
                                "        self\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/client.rs", "text": "pub struct Client"},
                {"type": "file_contains", "path": "src/client.rs", "text": "pub fn with_timeout"},
            ],
        },
        {
            "id": "rs-05-patch-borrow-check",
            "prompt": "修复借用检查器提示的可变借用冲突",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [
                    {
                        "path": "src/buffer.rs",
                        "content": (
                            "pub fn process(data: &mut Vec<String>) {\n"
                            "    let first = &data[0];\n"
                            "    data.push(first.clone());\n"
                            "}\n"
                        ),
                    }
                ],
                "script": [
                    {
                        "tool_name": "patch_text",
                        "params": {
                            "path": "src/buffer.rs",
                            "search_block": "    let first = &data[0];\n    data.push(first.clone());",
                            "replace_block": "    let first = data[0].clone();\n    data.push(first);",
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/buffer.rs", "text": "let first = data[0].clone();"},
            ],
        },
        {
            "id": "rs-06-iterator-adapter",
            "prompt": "为自定义集合实现 Iterator Trait",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/iter.rs",
                            "content": (
                                "pub struct StepSequence {\n"
                                "    curr: u64,\n"
                                "    step: u64,\n"
                                "    limit: u64,\n"
                                "}\n\n"
                                "impl Iterator for StepSequence {\n"
                                "    type Item = u64;\n"
                                "    fn next(&mut self) -> Option<Self::Item> {\n"
                                "        if self.curr >= self.limit { return None; }\n"
                                "        let val = self.curr;\n"
                                "        self.curr += self.step;\n"
                                "        Some(val)\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/iter.rs", "text": "impl Iterator for StepSequence"},
                {"type": "file_contains", "path": "src/iter.rs", "text": "type Item = u64;"},
            ],
        },
        {
            "id": "rs-07-unit-test-cfg",
            "prompt": "在模块尾部编写 #[cfg(test)] 单元测试模块",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/math.rs",
                            "content": (
                                "pub fn add(a: i32, b: i32) -> i32 { a + b }\n\n"
                                "#[cfg(test)]\n"
                                "mod tests {\n"
                                "    use super::*;\n"
                                "    #[test]\n"
                                "    fn test_add() {\n"
                                "        assert_eq!(add(2, 3), 5);\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/math.rs", "text": "#[cfg(test)]"},
                {"type": "file_contains", "path": "src/math.rs", "text": "assert_eq!(add(2, 3), 5)"},
            ],
        },
        {
            "id": "rs-08-concurrency-arc-mutex",
            "prompt": "使用 Arc<Mutex<T>> 跨线程共享状态",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/state.rs",
                            "content": (
                                "use std::sync::{Arc, Mutex};\n\n"
                                "pub struct SharedCounter {\n"
                                "    counter: Arc<Mutex<u64>>,\n"
                                "}\n\n"
                                "impl SharedCounter {\n"
                                "    pub fn new() -> Self {\n"
                                "        Self { counter: Arc::new(Mutex::new(0)) }\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/state.rs", "text": "Arc<Mutex<u64>>"},
                {"type": "file_contains", "path": "src/state.rs", "text": "Arc::new(Mutex::new(0))"},
            ],
        },
        {
            "id": "rs-09-from-into-trait",
            "prompt": "为自定义标识符类型实现 From<&str> Trait",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/id.rs",
                            "content": (
                                "#[derive(Debug, PartialEq, Eq)]\n"
                                "pub struct TaskId(pub String);\n\n"
                                "impl From<&str> for TaskId {\n"
                                "    fn from(s: &str) -> Self {\n"
                                "        TaskId(s.to_string())\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/id.rs", "text": "pub struct TaskId(pub String);"},
                {"type": "file_contains", "path": "src/id.rs", "text": "impl From<&str> for TaskId"},
            ],
        },
        {
            "id": "rs-10-raii-drop-guard",
            "prompt": "实现 Drop Trait 确保资源离开作用域时自动释放",
            "expected_status": "completed",
            "mode": "agent",
            "input": {
                "max_turns": 4,
                "files": [],
                "script": [
                    {
                        "tool_name": "write_text",
                        "params": {
                            "path": "src/guard.rs",
                            "content": (
                                "pub struct ResourceGuard {\n"
                                "    pub resource_id: String,\n"
                                "}\n\n"
                                "impl Drop for ResourceGuard {\n"
                                "    fn drop(&mut self) {\n"
                                "        // Automatic RAII resource clean up\n"
                                "    }\n"
                                "}\n"
                            ),
                        },
                    }
                ],
            },
            "assertions": [
                {"type": "file_contains", "path": "src/guard.rs", "text": "impl Drop for ResourceGuard"},
                {"type": "file_contains", "path": "src/guard.rs", "text": "fn drop(&mut self)"},
            ],
        },
    ]

    for task in tasks:
        path = tasks_dir / f"{task['id']}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(str(path))
    return created


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    tasks_base = repo_root / "benchmarks" / "tasks"
    go_tasks = generate_golang_tasks(tasks_base)
    ts_tasks = generate_typescript_tasks(tasks_base)
    rs_tasks = generate_rust_tasks(tasks_base)
    print(f"Generated {len(go_tasks)} Go tasks, {len(ts_tasks)} TypeScript tasks, {len(rs_tasks)} Rust tasks.")


if __name__ == "__main__":
    main()
