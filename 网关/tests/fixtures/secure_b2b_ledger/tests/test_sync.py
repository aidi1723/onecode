from __future__ import annotations

import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from sync_node import httpx, sync_inventory


class SyncNodeTest(unittest.TestCase):
    def test_sync_inventory_stops_after_retry_budget(self):
        snapshot = Path(__file__).resolve().parents[1] / "warehouse_snapshot.json"

        def fail_post(*args, **kwargs):
            try:
                raise httpx.ConnectError("manila node unavailable")
            except httpx.ConnectError:
                for _ in range(200):
                    print(f"DEBUG LEDGER TRACE: {traceback.format_exc()}")
                raise

        with patch("sync_node.httpx.post", side_effect=fail_post):
            result = sync_inventory("https://warehouse.invalid/sync", snapshot, max_retries=2)

        self.assertFalse(result["ok"])
        self.assertEqual(result["attempts"], 3)


if __name__ == "__main__":
    unittest.main()
