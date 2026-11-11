import json
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from onecode.kernel.wal import wal_entry_hash
from onecode.web.api import OneCodeRequestHandler
from onecode.web.metrics_collector import (
    collect_prometheus_metrics,
    format_prometheus_metrics,
)
from tests.test_web_api import local_test_server


class MetricsCollectorTests(unittest.TestCase):
    def test_collect_prometheus_metrics_base(self) -> None:
        lines = collect_prometheus_metrics()
        text = "\n".join(lines)
        self.assertIn("# HELP onecode_up", text)
        self.assertIn("# TYPE onecode_up gauge", text)
        self.assertIn("onecode_up 1", text)
        self.assertIn("# HELP onecode_info", text)
        self.assertIn('onecode_info{claims_mainstream_parity="false",service="onecode",version="1.1.0"} 1', text)
        self.assertIn("onecode_process_resident_memory_bytes", text)

    def test_collect_prometheus_metrics_with_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            wal_file = workspace / ".onecode" / "global-ledger.jsonl"
            wal_file.parent.mkdir(parents=True)
            entry = {
                "seq": 1,
                "ts": "2026-11-10T09:00:00Z",
                "rt": "low",
                "cm": "strict",
                "op": "commit",
                "prev": None,
            }
            entry["hash"] = wal_entry_hash(entry)
            wal_file.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

            runs_dir = workspace / ".onecode" / "runs" / "test-run"
            runs_dir.mkdir(parents=True)
            summary_file = runs_dir / "summary.json"
            summary_file.write_text(
                json.dumps({
                    "run_id": "test-run",
                    "status": "completed",
                    "iching_status_code": 63,
                }),
                encoding="utf-8",
            )

            lines = collect_prometheus_metrics(workspace)
            text = "\n".join(lines)
            self.assertIn("onecode_wal_entries_total", text)
            self.assertIn('risk_tier="low"', text)
            self.assertIn("onecode_runs_total", text)
            self.assertIn('status="missing"', text)

            raw = format_prometheus_metrics(workspace)
            self.assertTrue(isinstance(raw, bytes))
            self.assertTrue(raw.endswith(b"\n"))

    def test_http_metrics_endpoint_serves_openmetrics_text(self) -> None:
        with tempfile.TemporaryDirectory():
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                req = Request(f"{base_url}/metrics", method="GET")
                with urlopen(req, timeout=5) as resp:
                    status = resp.status
                    ctype = resp.headers.get("content-type")
                    body = resp.read().decode("utf-8")

                self.assertEqual(status, 200)
                self.assertEqual(ctype, "text/plain; version=0.0.4; charset=utf-8")
                self.assertIn("onecode_up 1", body)
                self.assertIn("onecode_info", body)

                # Test alias /v1/metrics
                req_v1 = Request(f"{base_url}/v1/metrics", method="GET")
                with urlopen(req_v1, timeout=5) as resp_v1:
                    self.assertEqual(resp_v1.status, 200)


if __name__ == "__main__":
    unittest.main()
