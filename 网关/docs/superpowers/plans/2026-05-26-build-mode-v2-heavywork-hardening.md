# Build Mode V2 Heavywork Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Build Mode from lightweight project generation into heavy industrial workloads by adding indexed sliding context windows for large repositories and incremental sandbox caches for slow build systems.

**Architecture:** Keep the existing two-instrument, four-scope, eight-primitive state model unchanged. Add V2 implementations under `离 101` and `震 001`: `离` gains a chunked repo index and evidence-backed context windows; `震` gains cache-aware isolated execution with immutable cache manifests and timeout/failure gates.

**Tech Stack:** Python 3, dataclasses, pathlib, hashlib, json, sqlite3, unittest, existing Build Mode modules, optional Docker/BuildKit/OverlayFS adapters behind injectable command runners.

---

## 1. Design Scope

This plan hardens two known MVP limits:

- Very large legacy repositories where a full repo card would exceed prompt and protocol limits.
- Heavy C/C++ or multi-language build systems where clean ephemeral containers make every retry pay the full compilation cost.

This plan does not change the hexagram codes, gateway authentication, or existing scoped-write rules.

## 2. Existing Files To Preserve

| File | Constraint |
| --- | --- |
| `agent_skill_dictionary/build_mode_types.py` | Add DTOs without breaking existing DTO serialization or constants. |
| `agent_skill_dictionary/build_mode_sandbox.py` | Extend with cache policy; existing no-cache behavior remains default. |
| `agent_skill_dictionary/build_mode_runner.py` | Add optional heavywork paths behind explicit profile decisions. |
| `agent_skill_dictionary/build_mode_intent.py` | Add profiling signals without changing simple task routing. |
| `agent_skill_dictionary/build_mode_permissions.py` | Keep `101/011` tool clearing semantics intact. |

## 3. New Files

| File | Responsibility |
| --- | --- |
| `agent_skill_dictionary/build_mode_repo_index.py` | Build and query a chunked repository index for `离 101` sliding windows. |
| `agent_skill_dictionary/build_mode_context_window.py` | Convert query results, failing line refs, and changed files into bounded prompt cards. |
| `agent_skill_dictionary/build_mode_compile_cache.py` | Describe, validate, and hash incremental build cache layers for `震 001`. |
| `tests/test_build_mode_repo_index.py` | Repository chunking, symbol extraction, and query ranking tests. |
| `tests/test_build_mode_context_window.py` | Token/character budget enforcement and evidence generation tests. |
| `tests/test_build_mode_compile_cache.py` | Cache key, manifest, and unsafe cache rejection tests. |
| `tests/test_build_mode_heavywork_profile.py` | Heavy repository and heavy build detection tests. |

## 4. New DTOs

Add these DTOs to `agent_skill_dictionary/build_mode_types.py`.

```python
@dataclass(frozen=True)
class HeavyTaskProfile:
    large_repo: bool
    heavy_build: bool
    repo_file_count: int
    repo_bytes: int
    build_markers: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RepoChunkEvidence:
    index_path: str
    repo_root: str
    indexed_files: int
    indexed_chunks: int
    skipped_files: tuple[str, ...]
    index_sha256: str


@dataclass(frozen=True)
class ContextWindowEvidence:
    source_index_sha256: str
    target_files: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    char_budget: int
    emitted_chars: int
    window_sha256: str


@dataclass(frozen=True)
class SandboxCacheEvidence:
    cache_key: str
    cache_root: str
    manifest_path: str
    restored: bool
    stored: bool
    cache_sha256: str
    readonly_layers: tuple[str, ...]
```

Hard rule: a model text claim such as "I indexed the repo" or "the cache is valid" is never accepted as one of these DTOs.

## 5. Task 1: Add Heavywork DTOs

**Files:**
- Modify: `agent_skill_dictionary/build_mode_types.py`
- Test: `tests/test_build_mode_types.py`

- [ ] **Step 1: Write failing DTO tests**

Append to `tests/test_build_mode_types.py`:

```python
from agent_skill_dictionary.build_mode_types import (
    ContextWindowEvidence,
    HeavyTaskProfile,
    RepoChunkEvidence,
    SandboxCacheEvidence,
)


class BuildModeHeavyworkTypesTest(unittest.TestCase):
    def test_heavy_profile_records_large_repo_and_build_markers(self):
        profile = HeavyTaskProfile(
            large_repo=True,
            heavy_build=True,
            repo_file_count=12000,
            repo_bytes=500_000_000,
            build_markers=("CMakeLists.txt", "compile_commands.json"),
            reasons=("repo_file_count>=5000", "cmake_marker"),
        )
        self.assertTrue(profile.large_repo)
        self.assertTrue(profile.heavy_build)
        self.assertIn("cmake_marker", profile.reasons)

    def test_context_window_evidence_has_budget_and_digest(self):
        evidence = ContextWindowEvidence(
            source_index_sha256="a" * 64,
            target_files=("src/service.cpp",),
            chunk_ids=("src/service.cpp:0", "src/service.cpp:1"),
            char_budget=12000,
            emitted_chars=8000,
            window_sha256="b" * 64,
        )
        self.assertLessEqual(evidence.emitted_chars, evidence.char_budget)

    def test_cache_evidence_separates_restore_and_store(self):
        evidence = SandboxCacheEvidence(
            cache_key="linux-cmake-a1",
            cache_root=".yizijue/cache/build/linux-cmake-a1",
            manifest_path=".yizijue/cache/build/linux-cmake-a1/manifest.json",
            restored=True,
            stored=False,
            cache_sha256="c" * 64,
            readonly_layers=("deps", "objects"),
        )
        self.assertTrue(evidence.restored)
        self.assertFalse(evidence.stored)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_types.BuildModeHeavyworkTypesTest
```

Expected: import error for the new DTO names.

- [ ] **Step 3: Implement DTOs**

Add the DTO classes from section 4 to `agent_skill_dictionary/build_mode_types.py`.

- [ ] **Step 4: Run the focused test and verify pass**

Run:

```bash
python3 -m unittest tests.test_build_mode_types.BuildModeHeavyworkTypesTest
```

Expected: `OK`.

## 6. Task 2: Add Heavy Task Profiling

**Files:**
- Modify: `agent_skill_dictionary/build_mode_intent.py`
- Test: `tests/test_build_mode_heavywork_profile.py`

- [ ] **Step 1: Write failing profile tests**

Create `tests/test_build_mode_heavywork_profile.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_intent import profile_heavy_task


class BuildModeHeavyworkProfileTest(unittest.TestCase):
    def test_detects_cmake_heavy_build_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CMakeLists.txt").write_text("project(mesh)\n", encoding="utf-8")
            profile = profile_heavy_task(str(root))
            self.assertTrue(profile.heavy_build)
            self.assertIn("CMakeLists.txt", profile.build_markers)

    def test_detects_large_repo_by_file_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for idx in range(12):
                (root / f"file_{idx}.py").write_text("x = 1\n", encoding="utf-8")
            profile = profile_heavy_task(str(root), large_file_threshold=10)
            self.assertTrue(profile.large_repo)
            self.assertIn("repo_file_count>=10", profile.reasons)

    def test_empty_repo_is_not_heavy(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = profile_heavy_task(tmp)
            self.assertFalse(profile.large_repo)
            self.assertFalse(profile.heavy_build)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_heavywork_profile
```

Expected: import error for `profile_heavy_task`.

- [ ] **Step 3: Implement profiling**

Add this function to `agent_skill_dictionary/build_mode_intent.py`:

```python
from pathlib import Path

from agent_skill_dictionary.build_mode_types import HeavyTaskProfile


HEAVY_BUILD_MARKERS = (
    "CMakeLists.txt",
    "compile_commands.json",
    "Makefile",
    "WORKSPACE",
    "BUILD.bazel",
    "Cargo.lock",
    "pnpm-lock.yaml",
)


def profile_heavy_task(
    workspace_root: str,
    *,
    large_file_threshold: int = 5000,
    large_byte_threshold: int = 100_000_000,
) -> HeavyTaskProfile:
    root = Path(workspace_root).resolve()
    file_count = 0
    total_bytes = 0
    markers: list[str] = []
    reasons: list[str] = []

    if not root.exists():
        return HeavyTaskProfile(False, False, 0, 0, (), ("workspace_missing",))

    for path in root.rglob("*"):
        if path.is_dir():
            if path.name in {".git", ".venv", "node_modules", "__pycache__"}:
                continue
            marker_name = path.name
        else:
            marker_name = path.name
            file_count += 1
            try:
                total_bytes += path.stat().st_size
            except OSError:
                continue

        if marker_name in HEAVY_BUILD_MARKERS and marker_name not in markers:
            markers.append(marker_name)

    if file_count >= large_file_threshold:
        reasons.append(f"repo_file_count>={large_file_threshold}")
    if total_bytes >= large_byte_threshold:
        reasons.append(f"repo_bytes>={large_byte_threshold}")
    if markers:
        reasons.append("heavy_build_marker")

    return HeavyTaskProfile(
        large_repo=file_count >= large_file_threshold or total_bytes >= large_byte_threshold,
        heavy_build=bool(markers),
        repo_file_count=file_count,
        repo_bytes=total_bytes,
        build_markers=tuple(sorted(markers)),
        reasons=tuple(reasons),
    )
```

- [ ] **Step 4: Run profile tests**

Run:

```bash
python3 -m unittest tests.test_build_mode_heavywork_profile
```

Expected: `OK`.

## 7. Task 3: Implement Chunked Repo Index For 离 101

**Files:**
- Create: `agent_skill_dictionary/build_mode_repo_index.py`
- Test: `tests/test_build_mode_repo_index.py`

- [ ] **Step 1: Write failing index tests**

Create `tests/test_build_mode_repo_index.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_repo_index import build_repo_index, query_repo_index


class BuildModeRepoIndexTest(unittest.TestCase):
    def test_index_skips_vendor_and_binary_like_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "crypto.py").write_text("def issue_key():\n    return 'k'\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "junk.js").write_text("ignored\n", encoding="utf-8")
            evidence = build_repo_index(str(root), max_chunk_chars=40)
            self.assertEqual(evidence.indexed_files, 1)
            self.assertGreaterEqual(evidence.indexed_chunks, 1)

    def test_query_returns_relevant_chunk_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "crypto.py").write_text("def encrypt_payload(data):\n    return data\n", encoding="utf-8")
            evidence = build_repo_index(str(root), max_chunk_chars=80)
            result = query_repo_index(evidence.index_path, "encrypt payload", limit=2)
            self.assertEqual(result[0]["path"], "crypto.py")
            self.assertIn("encrypt_payload", result[0]["text"])
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_repo_index
```

Expected: import error for `build_mode_repo_index`.

- [ ] **Step 3: Implement index module**

Create `agent_skill_dictionary/build_mode_repo_index.py` with:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agent_skill_dictionary.build_mode_types import RepoChunkEvidence


SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
TEXT_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".cpp", ".hpp", ".h", ".c", ".cc"}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix not in TEXT_EXTS:
            continue
        yield path


def _chunks(text: str, max_chunk_chars: int):
    for start in range(0, len(text), max_chunk_chars):
        yield start // max_chunk_chars, text[start : start + max_chunk_chars]


def build_repo_index(workspace_root: str, *, max_chunk_chars: int = 4000) -> RepoChunkEvidence:
    root = Path(workspace_root).resolve()
    index_dir = root / ".yizijue" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "repo-index.jsonl"

    indexed_files = 0
    indexed_chunks = 0
    skipped: list[str] = []
    records: list[dict[str, str | int]] = []

    for path in _iter_text_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(rel)
            continue
        indexed_files += 1
        for chunk_no, chunk_text in _chunks(text, max_chunk_chars):
            records.append({
                "chunk_id": f"{rel}:{chunk_no}",
                "path": rel,
                "text": chunk_text,
                "sha256": _sha256_text(chunk_text),
            })
            indexed_chunks += 1

    payload = "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
    index_path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")

    return RepoChunkEvidence(
        index_path=index_path.as_posix(),
        repo_root=root.as_posix(),
        indexed_files=indexed_files,
        indexed_chunks=indexed_chunks,
        skipped_files=tuple(skipped),
        index_sha256=_sha256_text(payload),
    )


def query_repo_index(index_path: str, query: str, *, limit: int = 8) -> list[dict[str, str]]:
    terms = {term.lower() for term in query.replace("_", " ").split() if term.strip()}
    rows: list[tuple[int, dict[str, str]]] = []
    path = Path(index_path)
    if not path.exists():
        return []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        haystack = f"{record['path']} {record['text']}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            rows.append((score, record))
    rows.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [record for _, record in rows[:limit]]
```

- [ ] **Step 4: Run index tests**

Run:

```bash
python3 -m unittest tests.test_build_mode_repo_index
```

Expected: `OK`.

## 8. Task 4: Implement Bounded Context Windows

**Files:**
- Create: `agent_skill_dictionary/build_mode_context_window.py`
- Test: `tests/test_build_mode_context_window.py`

- [ ] **Step 1: Write failing context-window tests**

Create `tests/test_build_mode_context_window.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_context_window import build_context_window
from agent_skill_dictionary.build_mode_repo_index import build_repo_index


class BuildModeContextWindowTest(unittest.TestCase):
    def test_window_respects_character_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "service.py").write_text("def target():\n    return 1\n" * 40, encoding="utf-8")
            index = build_repo_index(str(root), max_chunk_chars=120)
            card, evidence = build_context_window(index, "target", char_budget=500)
            self.assertLessEqual(len(card), 500)
            self.assertLessEqual(evidence.emitted_chars, 500)

    def test_window_mentions_target_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "crypto.py").write_text("def encrypt_payload(data):\n    return data\n", encoding="utf-8")
            index = build_repo_index(str(root), max_chunk_chars=120)
            card, evidence = build_context_window(index, "encrypt_payload", char_budget=1000)
            self.assertIn("crypto.py", card)
            self.assertEqual(evidence.target_files, ("crypto.py",))
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_context_window
```

Expected: import error for `build_mode_context_window`.

- [ ] **Step 3: Implement context window builder**

Create `agent_skill_dictionary/build_mode_context_window.py`:

```python
from __future__ import annotations

import hashlib

from agent_skill_dictionary.build_mode_repo_index import query_repo_index
from agent_skill_dictionary.build_mode_types import ContextWindowEvidence, RepoChunkEvidence


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_context_window(
    index: RepoChunkEvidence,
    query: str,
    *,
    char_budget: int = 12000,
    limit: int = 8,
) -> tuple[str, ContextWindowEvidence]:
    selected = query_repo_index(index.index_path, query, limit=limit)
    parts: list[str] = []
    target_files: list[str] = []
    chunk_ids: list[str] = []

    for record in selected:
        header = f"\n# {record['path']} [{record['chunk_id']}]\n"
        body = str(record["text"])
        candidate = "".join(parts) + header + body
        if len(candidate) > char_budget:
            remaining = char_budget - len("".join(parts)) - len(header)
            if remaining <= 0:
                break
            body = body[:remaining]
        parts.append(header + body)
        if record["path"] not in target_files:
            target_files.append(record["path"])
        chunk_ids.append(record["chunk_id"])
        if len("".join(parts)) >= char_budget:
            break

    card = "".join(parts)[:char_budget]
    evidence = ContextWindowEvidence(
        source_index_sha256=index.index_sha256,
        target_files=tuple(target_files),
        chunk_ids=tuple(chunk_ids),
        char_budget=char_budget,
        emitted_chars=len(card),
        window_sha256=_digest(card),
    )
    return card, evidence
```

- [ ] **Step 4: Run context-window tests**

Run:

```bash
python3 -m unittest tests.test_build_mode_context_window
```

Expected: `OK`.

## 9. Task 5: Add Incremental Sandbox Cache Metadata

**Files:**
- Create: `agent_skill_dictionary/build_mode_compile_cache.py`
- Test: `tests/test_build_mode_compile_cache.py`

- [ ] **Step 1: Write failing compile-cache tests**

Create `tests/test_build_mode_compile_cache.py`:

```python
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_compile_cache import build_cache_key, write_cache_manifest


class BuildModeCompileCacheTest(unittest.TestCase):
    def test_cache_key_changes_when_lockfile_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CMakeLists.txt").write_text("project(a)\n", encoding="utf-8")
            key1 = build_cache_key(str(root), command="cmake --build build")
            (root / "CMakeLists.txt").write_text("project(b)\n", encoding="utf-8")
            key2 = build_cache_key(str(root), command="cmake --build build")
            self.assertNotEqual(key1, key2)

    def test_manifest_records_readonly_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = write_cache_manifest(
                cache_root=tmp,
                cache_key="linux-cmake-a1",
                restored=False,
                stored=True,
                readonly_layers=("deps", "objects"),
            )
            self.assertTrue(Path(evidence.manifest_path).exists())
            self.assertEqual(evidence.readonly_layers, ("deps", "objects"))
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_compile_cache
```

Expected: import error for `build_mode_compile_cache`.

- [ ] **Step 3: Implement compile-cache metadata**

Create `agent_skill_dictionary/build_mode_compile_cache.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agent_skill_dictionary.build_mode_types import SandboxCacheEvidence


CACHE_INPUT_FILES = (
    "CMakeLists.txt",
    "compile_commands.json",
    "Makefile",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_cache_key(workspace_root: str, *, command: str) -> str:
    root = Path(workspace_root).resolve()
    digest = hashlib.sha256()
    digest.update(command.encode("utf-8"))
    for rel in CACHE_INPUT_FILES:
        path = root / rel
        if path.exists() and path.is_file():
            digest.update(rel.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()[:24]


def write_cache_manifest(
    *,
    cache_root: str,
    cache_key: str,
    restored: bool,
    stored: bool,
    readonly_layers: tuple[str, ...],
) -> SandboxCacheEvidence:
    root = Path(cache_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    payload = {
        "cache_key": cache_key,
        "cache_root": root.as_posix(),
        "restored": restored,
        "stored": stored,
        "readonly_layers": list(readonly_layers),
    }
    raw = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    manifest_path.write_bytes(raw)
    return SandboxCacheEvidence(
        cache_key=cache_key,
        cache_root=root.as_posix(),
        manifest_path=manifest_path.as_posix(),
        restored=restored,
        stored=stored,
        cache_sha256=_sha256_bytes(raw),
        readonly_layers=readonly_layers,
    )
```

- [ ] **Step 4: Run compile-cache tests**

Run:

```bash
python3 -m unittest tests.test_build_mode_compile_cache
```

Expected: `OK`.

## 10. Task 6: Integrate Cache Evidence Into 震 001

**Files:**
- Modify: `agent_skill_dictionary/build_mode_sandbox.py`
- Test: `tests/test_build_mode_sandbox.py`

- [ ] **Step 1: Add no-cache compatibility test**

Append to `tests/test_build_mode_sandbox.py`:

```python
class BuildModeSandboxCacheCompatibilityTest(unittest.TestCase):
    def test_default_sandbox_run_has_no_cache_evidence(self):
        result = run_isolated_test(
            "python3 -c 'print(123)'",
            workspace_root=".",
            timeout_seconds=5,
            use_docker=False,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(hasattr(result, "cache_evidence"))
```

- [ ] **Step 2: Add cache-enabled test**

Append:

```python
    def test_cache_enabled_run_records_cache_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_isolated_test(
                "python3 -c 'print(123)'",
                workspace_root=tmp,
                timeout_seconds=5,
                use_docker=False,
                cache_mode="metadata_only",
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIsNotNone(result.cache_evidence)
            self.assertTrue(Path(result.cache_evidence.manifest_path).exists())
```

- [ ] **Step 3: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_sandbox.BuildModeSandboxCacheCompatibilityTest
```

Expected: failure because `cache_mode` and `cache_evidence` are not implemented.

- [ ] **Step 4: Implement optional cache_mode**

Update `run_isolated_test()` so default behavior is unchanged. When `cache_mode="metadata_only"`, compute `cache_key`, create `.yizijue/cache/build/<cache_key>/manifest.json`, and attach `SandboxCacheEvidence` to the returned evidence object.

Implementation constraints:

- Do not restore arbitrary host directories.
- Do not cache `.env`, secrets, `.ssh`, `.codex`, `.claude`, or user home paths.
- `metadata_only` is the first implementation. Real Docker/BuildKit cache restore is a later adapter behind the same DTO.

- [ ] **Step 5: Run sandbox cache tests**

Run:

```bash
python3 -m unittest tests.test_build_mode_sandbox.BuildModeSandboxCacheCompatibilityTest
```

Expected: `OK`.

## 11. Task 7: Wire Large Repo Windows Into 离 101

**Files:**
- Modify: `agent_skill_dictionary/build_mode_runner.py`
- Modify: `agent_skill_dictionary/build_mode_feedback.py`
- Test: `tests/test_build_mode_runner.py`

- [ ] **Step 1: Add failing runner test**

Add a test that creates three source files, triggers a failure query for one symbol, and asserts the returned repo card includes only the relevant file and stays below a fixed budget:

```python
def test_failed_run_uses_bounded_context_window_for_large_repo(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text("def unrelated():\n    return 1\n", encoding="utf-8")
        (root / "crypto.py").write_text("def encrypt_payload(data):\n    raise ValueError('bad')\n", encoding="utf-8")
        (root / "server.py").write_text("def handler():\n    return encrypt_payload('x')\n", encoding="utf-8")
        runner = BuildModeRunner(workspace_root=str(root), context_char_budget=800)
        card, evidence = runner.build_inspection_window("encrypt_payload")
        self.assertIn("crypto.py", card)
        self.assertLessEqual(len(card), 800)
        self.assertLessEqual(evidence.emitted_chars, 800)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python3 -m unittest tests.test_build_mode_runner.BuildModeRunnerTest.test_failed_run_uses_bounded_context_window_for_large_repo
```

Expected: failure because `build_inspection_window()` is missing.

- [ ] **Step 3: Implement `BuildModeRunner.build_inspection_window()`**

The method should:

1. Call `build_repo_index(self.workspace_root)`.
2. Call `build_context_window(index, query, char_budget=self.context_char_budget)`.
3. Return `(card, ContextWindowEvidence)`.

- [ ] **Step 4: Run runner focused test**

Run:

```bash
python3 -m unittest tests.test_build_mode_runner.BuildModeRunnerTest.test_failed_run_uses_bounded_context_window_for_large_repo
```

Expected: `OK`.

## 12. Task 8: Add Safety Gates For Cache And Window Paths

**Files:**
- Modify: `agent_skill_dictionary/build_mode_repo_index.py`
- Modify: `agent_skill_dictionary/build_mode_compile_cache.py`
- Test: `tests/test_build_mode_repo_index.py`
- Test: `tests/test_build_mode_compile_cache.py`

- [ ] **Step 1: Add secret-path rejection tests**

Append to repo index tests:

```python
def test_index_never_reads_secret_directories(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".codex" / "auth.json").write_text('{"token":"secret"}', encoding="utf-8")
        evidence = build_repo_index(str(root), max_chunk_chars=100)
        rows = Path(evidence.index_path).read_text(encoding="utf-8")
        self.assertNotIn("secret", rows)
        self.assertEqual(evidence.indexed_files, 0)
```

Append to compile-cache tests:

```python
def test_cache_key_ignores_secret_files(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
        key1 = build_cache_key(str(root), command="pytest")
        (root / ".env").write_text("TOKEN=changed\n", encoding="utf-8")
        key2 = build_cache_key(str(root), command="pytest")
        self.assertEqual(key1, key2)
```

- [ ] **Step 2: Run and verify failures if current code leaks secrets**

Run:

```bash
python3 -m unittest tests.test_build_mode_repo_index tests.test_build_mode_compile_cache
```

Expected: repo index should fail until `.codex` and secret files are explicitly skipped.

- [ ] **Step 3: Add secret skip lists**

Update both modules with:

```python
SECRET_NAMES = {".env", "auth.json", "id_rsa", "id_ed25519"}
SECRET_DIRS = {".ssh", ".codex", ".claude", ".config"}
```

Skip any path where a path component is in `SECRET_DIRS` or the filename is in `SECRET_NAMES`.

- [ ] **Step 4: Run safety tests**

Run:

```bash
python3 -m unittest tests.test_build_mode_repo_index tests.test_build_mode_compile_cache
```

Expected: `OK`.

## 13. Task 9: Document Runtime Policy

**Files:**
- Modify: `docs/build-mode-control-network.md`
- Modify: `docs/build-mode-mvp-implementation-plan.md`

- [ ] **Step 1: Add V2 heavywork policy section**

Add this section to `docs/build-mode-control-network.md`:

```markdown
## V2 Heavywork Policy

Large repositories and heavy builds do not change the eight primitive state codes.
They change the physical implementation strategy inside two primitives:

- `离 101`: full repo cards are replaced by indexed sliding context windows.
- `震 001`: throwaway sandboxes are replaced by isolated cache-aware sandboxes when heavy build markers are present.

Completion still requires structured evidence. `ContextWindowEvidence` and
`SandboxCacheEvidence` supplement existing evidence; they do not replace
`SandboxEvidence` or `ArchiveEvidence`.
```

- [ ] **Step 2: Add MVP/V2 boundary note**

Add this section to `docs/build-mode-mvp-implementation-plan.md`:

```markdown
## MVP/V2 Boundary

MVP covers lightweight project generation and Python-style verification.
V2 heavywork hardening adds large-repo sliding windows and incremental build
cache metadata. V2 must remain optional and evidence-gated so the MVP behavior
continues to pass unchanged.
```

- [ ] **Step 3: Verify docs contain the new policy**

Run:

```bash
rg -n "V2 Heavywork Policy|MVP/V2 Boundary" docs/build-mode-control-network.md docs/build-mode-mvp-implementation-plan.md
```

Expected: both headings found.

## 14. Task 10: Full Verification

**Files:**
- All files modified by this plan.

- [ ] **Step 1: Run focused heavywork tests**

Run:

```bash
python3 -m unittest \
  tests.test_build_mode_types \
  tests.test_build_mode_heavywork_profile \
  tests.test_build_mode_repo_index \
  tests.test_build_mode_context_window \
  tests.test_build_mode_compile_cache \
  tests.test_build_mode_sandbox \
  tests.test_build_mode_runner
```

Expected: all tests pass.

- [ ] **Step 2: Run Build Mode regression tests**

Run:

```bash
python3 -m unittest \
  tests.test_build_mode_intent \
  tests.test_build_mode_permissions \
  tests.test_build_mode_tool_executor \
  tests.test_build_mode_gateway_integration \
  tests.test_gateway_server_import
```

Expected: all tests pass.

- [ ] **Step 3: Compile check**

Run:

```bash
python3 -m compileall -q agent_skill_dictionary scripts tests
```

Expected: exit code `0`.

## 15. Acceptance Criteria

- `离 101` can produce a bounded context window from a large repo index without emitting full-repo contents.
- Secret directories and secret files are never indexed, cached, or surfaced in repo cards.
- `震 001` can emit cache metadata for heavy builds without changing default no-cache sandbox behavior.
- Cache evidence is structured and hash-backed; model claims do not unlock cache reuse.
- Existing Build Mode MVP tests continue to pass unchanged.
- Documentation states that V2 extends implementation strategy, not the underlying state model.

## 16. Execution Notes

Implement this plan in a separate worktree or branch. Commit after each task that passes its focused tests. Do not enable real Docker/BuildKit cache restore by default until metadata-only cache evidence has passed the full regression suite.
