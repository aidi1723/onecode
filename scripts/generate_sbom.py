#!/usr/bin/env python3
"""Standard-library Software Bill of Materials (SBOM) & License Governance Generator.

Generates CycloneDX 1.5 and SPDX 2.3 compliant SBOMs with:
- Strict zero-dependency declaration (runtime dependencies = [])
- Cryptographic SHA-256 checksums for every source asset
- Aggregate release tree provenance hash
- License governance verification (GPL-3.0-only declaration match)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from onecode import __version__

ROOT = Path(__file__).resolve().parent.parent


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def collect_source_components(root_dir: Path | None = None) -> list[dict[str, Any]]:
    """Scan all source files under src/onecode and build component manifests."""
    root = (root_dir or ROOT).resolve()
    src_dir = root / "src" / "onecode"
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src_dir}")

    components: list[dict[str, Any]] = []
    for file_path in sorted(src_dir.rglob("*")):
        if not file_path.is_file() or file_path.suffix in {".pyc", ".pyo"}:
            continue
        rel_path = file_path.relative_to(root).as_posix()
        sha256 = compute_file_sha256(file_path)
        size_bytes = file_path.stat().st_size
        mime = "text/x-python" if file_path.suffix == ".py" else "application/octet-stream"
        if file_path.suffix == ".json":
            mime = "application/json"
        elif file_path.suffix == ".html":
            mime = "text/html"

        components.append({
            "name": rel_path,
            "version": __version__,
            "type": "file",
            "path": rel_path,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "mime_type": mime,
            "license": "GPL-3.0-only",
        })
    return components


def compute_provenance_tree_hash(components: list[dict[str, Any]]) -> str:
    """Compute an aggregate Merkle tree digest across all source components."""
    hasher = hashlib.sha256()
    for comp in sorted(components, key=lambda c: str(c["path"])):
        hasher.update(f"{comp['path']}:{comp['sha256']}\n".encode("utf-8"))
    return hasher.hexdigest()


def generate_cyclonedx_sbom(components: list[dict[str, Any]], tree_hash: str) -> dict[str, Any]:
    """Generate CycloneDX 1.5 JSON SBOM."""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:onecode-kernel-{tree_hash[:16]}",
        "version": 1,
        "metadata": {
            "timestamp": "2026-11-05T00:00:00Z",
            "tools": [{"vendor": "OneCode", "name": "onecode-sbom-generator", "version": __version__}],
            "component": {
                "type": "application",
                "name": "onecode-kernel",
                "version": __version__,
                "description": "Local-first agent kernel with guarded model plan execution",
                "licenses": [{"license": {"id": "GPL-3.0-only"}}],
                "hashes": [{"alg": "SHA-256", "content": tree_hash}],
            },
            "properties": [
                {"name": "onecode:runtime_dependencies_count", "value": "0"},
                {"name": "onecode:standard_library_only", "value": "true"},
            ],
        },
        "components": [
            {
                "type": "file",
                "name": comp["name"],
                "version": comp["version"],
                "hashes": [{"alg": "SHA-256", "content": comp["sha256"]}],
                "licenses": [{"license": {"id": comp["license"]}}],
            }
            for comp in components
        ],
        "dependencies": [
            {
                "ref": "onecode-kernel",
                "dependsOn": [],  # Pure standard library - no external runtime dependencies
            }
        ],
    }


def generate_spdx_sbom(components: list[dict[str, Any]], tree_hash: str) -> dict[str, Any]:
    """Generate SPDX 2.3 JSON SBOM."""
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "onecode-kernel",
        "documentNamespace": f"https://github.com/aidi1723/onecode/spdx/{tree_hash[:16]}",
        "creationInfo": {
            "created": "2026-11-05T00:00:00Z",
            "creators": [f"Tool: onecode-sbom-generator-{__version__}", "Organization: OneCode"],
        },
        "packages": [
            {
                "SPDXID": "SPDXRef-Package-onecode-kernel",
                "name": "onecode-kernel",
                "versionInfo": __version__,
                "packageFileName": f"onecode-kernel-{__version__}.tar.gz",
                "supplier": "Organization: OneCode",
                "downloadLocation": "https://github.com/aidi1723/onecode",
                "filesAnalyzed": True,
                "checksums": [{"algorithm": "SHA256", "checksumValue": tree_hash}],
                "licenseConcluded": "GPL-3.0-only",
                "licenseDeclared": "GPL-3.0-only",
                "description": "Guarded local-first agent kernel with zero runtime dependencies.",
            }
        ],
        "files": [
            {
                "SPDXID": f"SPDXRef-File-{idx}",
                "fileName": comp["path"],
                "checksums": [{"algorithm": "SHA256", "checksumValue": comp["sha256"]}],
                "licenseConcluded": comp["license"],
            }
            for idx, comp in enumerate(components)
        ],
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relatedSpdxElement": "SPDXRef-Package-onecode-kernel",
                "relationshipType": "DESCRIBES",
            }
        ],
    }


def verify_license_governance(pyproject_path: Path | None = None) -> dict[str, Any]:
    """Verify license compliance and runtime dependency purity."""
    path = (pyproject_path or ROOT / "pyproject.toml").resolve()
    if not path.is_file():
        raise FileNotFoundError(f"pyproject.toml not found at: {path}")

    import tomllib

    with open(path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    declared_license = str(project.get("license") or "")
    deps = project.get("dependencies", [])

    is_license_compliant = declared_license == "GPL-3.0-only"
    is_deps_clean = isinstance(deps, list) and len(deps) == 0

    return {
        "status": "compliant" if is_license_compliant and is_deps_clean else "violation",
        "declared_license": declared_license,
        "is_license_compliant": is_license_compliant,
        "runtime_dependencies": deps,
        "is_zero_dependencies": is_deps_clean,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OneCode SBOM & License Governance Generator")
    parser.add_argument("--format", choices=["cyclonedx", "spdx", "both"], default="cyclonedx")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--verify-only", action="store_true", help="Only verify license and dependency purity")
    args = parser.parse_args()

    governance = verify_license_governance()
    if governance["status"] != "compliant":
        print(f"[GOVERNANCE VIOLATION] License or dependencies unclean: {governance}", file=sys.stderr)
        return 1

    if args.verify_only:
        print(json.dumps(governance, indent=2, ensure_ascii=False))
        return 0

    components = collect_source_components()
    tree_hash = compute_provenance_tree_hash(components)

    if args.format == "cyclonedx":
        doc = generate_cyclonedx_sbom(components, tree_hash)
    elif args.format == "spdx":
        doc = generate_spdx_sbom(components, tree_hash)
    else:
        doc = {
            "cyclonedx": generate_cyclonedx_sbom(components, tree_hash),
            "spdx": generate_spdx_sbom(components, tree_hash),
        }

    output_str = json.dumps(doc, indent=2, ensure_ascii=False)
    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_str, encoding="utf-8")
        print(f"[SBOM SAVED] SBOM written to: {out_path} (tree_sha256={tree_hash})")
    else:
        print(output_str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
