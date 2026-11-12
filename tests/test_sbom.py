"""Tests for the Software Bill of Materials (SBOM) and License Governance Generator."""
from __future__ import annotations

import unittest

from scripts.generate_sbom import (
    collect_source_components,
    compute_provenance_tree_hash,
    generate_cyclonedx_sbom,
    generate_spdx_sbom,
    verify_license_governance,
)


class SbomGeneratorTests(unittest.TestCase):
    def test_verify_license_governance_complies(self) -> None:
        gov = verify_license_governance()
        self.assertEqual(gov["status"], "compliant")
        self.assertTrue(gov["is_zero_dependencies"])
        self.assertTrue(gov["is_license_compliant"])
        self.assertEqual(gov["declared_license"], "GPL-3.0-only")
        self.assertEqual(gov["runtime_dependencies"], [])

    def test_collect_source_components(self) -> None:
        components = collect_source_components()
        self.assertGreater(len(components), 50)
        first = components[0]
        self.assertIn("name", first)
        self.assertIn("sha256", first)
        self.assertEqual(len(first["sha256"]), 64)
        self.assertEqual(first["license"], "GPL-3.0-only")

    def test_provenance_tree_hash_is_deterministic(self) -> None:
        components = collect_source_components()
        hash1 = compute_provenance_tree_hash(components)
        hash2 = compute_provenance_tree_hash(components)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_generate_cyclonedx_sbom_has_zero_external_dependencies(self) -> None:
        components = collect_source_components()
        tree_hash = compute_provenance_tree_hash(components)
        doc = generate_cyclonedx_sbom(components, tree_hash)
        self.assertEqual(doc["bomFormat"], "CycloneDX")
        self.assertEqual(doc["specVersion"], "1.5")
        self.assertIn("metadata", doc)
        self.assertEqual(doc["dependencies"], [{"ref": "onecode-kernel", "dependsOn": []}])
        self.assertEqual(len(doc["components"]), len(components))

    def test_generate_spdx_sbom_structure(self) -> None:
        components = collect_source_components()
        tree_hash = compute_provenance_tree_hash(components)
        doc = generate_spdx_sbom(components, tree_hash)
        self.assertEqual(doc["spdxVersion"], "SPDX-2.3")
        self.assertEqual(len(doc["packages"]), 1)
        self.assertEqual(doc["packages"][0]["licenseDeclared"], "GPL-3.0-only")
        self.assertEqual(len(doc["files"]), len(components))


if __name__ == "__main__":
    unittest.main()
