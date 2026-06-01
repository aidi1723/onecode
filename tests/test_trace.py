import json
import tempfile
import unittest
from pathlib import Path


class TraceTests(unittest.TestCase):
    def test_write_trace_event_appends_jsonl(self):
        from onecode.kernel.trace import TraceEvent, write_trace_event

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            write_trace_event(
                path,
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="span-1",
                    parent_span_id=None,
                    event_type="run_started",
                    status="started",
                    payload={"task": "demo"},
                ),
            )
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["trace_id"], "trace-1")
        self.assertEqual(payload["event_type"], "run_started")
        self.assertIn("timestamp", payload)

    def test_trace_event_rejects_empty_event_type(self):
        from onecode.kernel.trace import TraceEvent

        with self.assertRaises(ValueError):
            TraceEvent(
                trace_id="trace-1",
                run_id="run-1",
                span_id="span-1",
                parent_span_id=None,
                event_type="",
                status="started",
                payload={},
            )
