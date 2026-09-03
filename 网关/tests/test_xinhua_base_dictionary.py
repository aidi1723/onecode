import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class XinhuaBaseDictionaryTest(unittest.TestCase):
    def setUp(self):
        entries_path = PROJECT_ROOT / "data" / "xinhua-base-entries.json"
        lookup_path = PROJECT_ROOT / "data" / "xinhua-base-lookup.json"
        self.entries = json.loads(entries_path.read_text(encoding="utf-8"))["entries"]
        self.lookup = json.loads(lookup_path.read_text(encoding="utf-8"))

    def test_variant_lookup_keys_map_to_one_modern_entry(self):
        owners_by_key = {}
        for entry in self.entries:
            for key in [entry["modern"], *entry.get("traditional_or_variants", [])]:
                owners_by_key.setdefault(key, set()).add(entry["modern"])

        ambiguous_keys = {
            key: sorted(owners)
            for key, owners in owners_by_key.items()
            if len(owners) > 1
        }

        self.assertEqual(ambiguous_keys, {})

    def test_hua_traditional_form_resolves_to_hua_not_flower(self):
        self.assertEqual(self.lookup["by_modern_or_variant"]["華"]["modern"], "华")
        flower = next(entry for entry in self.entries if entry["modern"] == "花")
        self.assertNotIn("華", flower["traditional_or_variants"])
        self.assertNotIn("華", flower.get("variant_unicodes", {}))


if __name__ == "__main__":
    unittest.main()
