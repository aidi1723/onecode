import re
from pathlib import Path

from onecode.kernel.checkpoint import sha256_text
from onecode.kernel.path_guard import PathGuard, PathGuardError


_ALLOW_WRITE = "ALLOW_ATOMIC_WRITE"
_ALLOW_PATCH = "ALLOW_PATCH_WITH_SHA"
_DENY = "DENY_AND_LEDGER"
_ABSOLUTE = re.compile(r"(?<![\w.])(/[^\s，,。；;]+)")
_RELATIVE = re.compile(
    r"(?<![A-Za-z0-9_./])(\./[^\s，,。；;：:'\"]+|(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|[A-Za-z0-9_-]+\.(?:py|json|ya?ml|txt|md|conf|toml|ini|csv))"
)
_WRITE_PATTERNS = (
    re.compile(r"把\s*['\"](?P<content>.*?)['\"]\s*写入\s*(?P<path>\S+)"),
    re.compile(r"写入\s+(?P<path>\S+?)\s*内容为\s*(?P<content>.+?)\s*$"),
    re.compile(r"(?P<path>\S+?)\s*写入内容\s*[:：]?\s*(?P<content>.+?)\s*$"),
    re.compile(r"写入内容\s*[:：]?\s*(?P<content>.+?)\s*$"),
    re.compile(r"以下内容写入.+?(?P<path>\S+?)\s*[:：]\s*(?P<content>.+)\s*$", re.S),
    re.compile(r"内容替换为\s*['\"](?P<content>.*?)['\"]"),
    re.compile(r"内容写入为\s*(?P<content>.+?)\s*$"),
    re.compile(r"内容更新为\s*(?P<content>.+?)\s*$"),
    re.compile(r"内容为\s*(?P<content>.+?)\s*$"),
    re.compile(r"[:：]\s*(?P<content>.+?)\s*$"),
)
_PATCH_PATTERN = re.compile(
    r"['\"](?P<search>.*?)['\"]\s*(?:替换为|修改为|改为)\s*['\"](?P<replace>.*?)['\"]"
)


def complete_allow_evidence(
    action: str,
    facts: dict[str, str],
    user_text: str,
    workspace_root: Path,
) -> dict[str, object]:
    """Attach path and content hashes, or deny when the request does not contain them."""
    if action not in {_ALLOW_WRITE, _ALLOW_PATCH}:
        return {"action": action, "facts": dict(facts), "reason": None, "evidence": None}
    if not isinstance(user_text, str):
        raise ValueError("user_text must be a string")
    relative_paths = _relative_paths(user_text, workspace_root)
    if _ABSOLUTE.search(user_text) or len(relative_paths) != 1:
        return _deny(facts, "evidence_not_extracted", None)
    path = relative_paths[0]
    if action == _ALLOW_WRITE:
        return _complete_write(facts, user_text, path)
    return _complete_patch(facts, user_text, path, workspace_root)


def _complete_write(facts: dict[str, str], user_text: str, path: str) -> dict[str, object]:
    content = _write_content(user_text, path)
    if content is None:
        return _deny(facts, "evidence_not_extracted", None)
    return {
        "action": _ALLOW_WRITE,
        "facts": dict(facts),
        "reason": None,
        "evidence": {"path": path, "sha256": sha256_text(content)},
    }


def _complete_patch(
    facts: dict[str, str],
    user_text: str,
    path: str,
    workspace_root: Path,
) -> dict[str, object]:
    match = _PATCH_PATTERN.search(user_text)
    if match is None:
        return _deny(facts, "evidence_not_extracted", None)
    search = match.group("search")
    replace = match.group("replace")
    evidence = {
        "path": path,
        "search_block_sha256": sha256_text(search),
        "replace_block_sha256": sha256_text(replace),
    }
    original = _read_workspace_text(workspace_root, path)
    if original is None:
        return _deny(facts, "file_digest_not_in_request", evidence)
    if original.count(search) != 1:
        return _deny(facts, "search_block_not_unique", evidence)
    updated = original.replace(search, replace, 1)
    evidence["pre_sha256"] = sha256_text(original)
    evidence["post_sha256"] = sha256_text(updated)
    return {"action": _ALLOW_PATCH, "facts": dict(facts), "reason": None, "evidence": evidence}


def _read_workspace_text(workspace_root: Path, relative_path: str) -> str | None:
    try:
        target = PathGuard.resolve_target(workspace_root, relative_path)
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeError, PathGuardError):
        return None


def _write_content(user_text: str, path: str) -> str | None:
    for pattern in _WRITE_PATTERNS:
        match = pattern.search(user_text)
        if match is None:
            continue
        named = match.groupdict()
        if "path" in named and _clean_token(named["path"]) not in {path, f"./{path}"}:
            continue
        content = _clean_content(named["content"])
        if content:
            return content
    return None


def _clean_content(content: str) -> str:
    content = content.strip().strip("'\"")
    if content.startswith("```"):
        content = re.sub(r"^```[A-Za-z]*\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip().strip("'\"")
    return content.removesuffix("。").strip()


def _relative_paths(user_text: str, workspace_root: Path) -> list[str]:
    found: list[str] = []
    for token in _RELATIVE.findall(user_text):
        cleaned = _clean_token(token)
        if cleaned in found or not _accepts(workspace_root, cleaned):
            continue
        found.append(cleaned)
    return found


def _accepts(workspace_root: Path, relative_path: str) -> bool:
    try:
        PathGuard.resolve_target(workspace_root, relative_path)
    except PathGuardError:
        return False
    return True


def _clean_token(token: str) -> str:
    return token.strip().strip("：:，,。；;")


def _deny(facts: dict[str, str], reason: str, evidence: dict[str, str] | None) -> dict[str, object]:
    return {"action": _DENY, "facts": dict(facts), "reason": reason, "evidence": evidence}
