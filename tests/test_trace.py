import json
import tempfile
import threading
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
        self.assertEqual(payload["risk_tier"], "medium")
        self.assertEqual(payload["capture_mode"], "compact")
        self.assertRegex(payload["payload_digest"], r"^[0-9a-f]{64}$")

    def test_write_trace_event_keeps_jsonl_valid_under_concurrent_writes(self):
        from onecode.kernel.trace import TraceEvent, write_trace_event

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            barrier = threading.Barrier(8)

            def write_batch(worker: int) -> None:
                barrier.wait()
                for index in range(40):
                    write_trace_event(
                        path,
                        TraceEvent(
                            trace_id="trace-1",
                            run_id="run-1",
                            span_id=f"worker-{worker}-{index}",
                            parent_span_id=None,
                            event_type="physical_write",
                            status="completed",
                            payload={"path": f"src/{worker}-{index}.py", "content": "x" * 500},
                        ),
                    )

            threads = [threading.Thread(target=write_batch, args=(worker,)) for worker in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 320)
        events = [json.loads(line) for line in lines]
        self.assertEqual(len({event["span_id"] for event in events}), 320)
        self.assertTrue(all(event["write_latency_ms"] != "000000.000" for event in events))

    def test_write_trace_event_does_not_patch_matching_payload_value(self):
        from onecode.kernel.trace import TraceEvent, write_trace_event

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            write_trace_event(
                path,
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="write-1",
                    parent_span_id=None,
                    event_type="physical_write",
                    status="completed",
                    payload={"value": "000000.000"},
                ),
            )
            event = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(event["payload"]["value"], "000000.000")
        self.assertNotEqual(event["write_latency_ms"], "000000.000")

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

    def test_unknown_trace_event_fails_closed_to_full_critical(self):
        from onecode.kernel.trace import TraceEvent

        event = TraceEvent(
            trace_id="trace-1",
            run_id="run-1",
            span_id="span-1",
            parent_span_id=None,
            event_type="new_runtime_event",
            status="observed",
            payload={"value": 1},
        )

        payload = event.to_dict()
        self.assertEqual(payload["risk_tier"], "critical")
        self.assertEqual(payload["capture_mode"], "full")
        self.assertEqual(payload["classification_reason"], "unknown_event_family_fail_closed")

    def test_trace_aggregator_coalesces_repeated_low_risk_events(self):
        from onecode.kernel.trace import TraceAggregator, TraceEvent

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            aggregator = TraceAggregator(path)

            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="heartbeat-1",
                    parent_span_id=None,
                    event_type="heartbeat",
                    status="ok",
                    payload={"node": "local"},
                    timestamp="2026-06-02T00:00:00+00:00",
                )
            )
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="heartbeat-2",
                    parent_span_id=None,
                    event_type="heartbeat",
                    status="ok",
                    payload={"node": "local"},
                    timestamp="2026-06-02T00:00:03+00:00",
                )
            )
            aggregator.flush()

            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["event_type"], "heartbeat_aggregate")
        self.assertEqual(lines[0]["capture_mode"], "aggregate")
        self.assertEqual(lines[0]["payload"]["count"], 2)
        self.assertEqual(lines[0]["payload"]["first_timestamp"], "2026-06-02T00:00:00+00:00")
        self.assertEqual(lines[0]["payload"]["last_timestamp"], "2026-06-02T00:00:03+00:00")
        self.assertRegex(lines[0]["payload"]["rolling_digest"], r"^[0-9a-f]{64}$")

    def test_trace_aggregator_never_coalesces_critical_events(self):
        from onecode.kernel.trace import TraceAggregator, TraceEvent

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            aggregator = TraceAggregator(path)

            for index in range(2):
                aggregator.record(
                    TraceEvent(
                        trace_id="trace-1",
                        run_id="run-1",
                        span_id=f"write-{index}",
                        parent_span_id=None,
                        event_type="physical_write",
                        status="completed",
                        payload={"path": f"src/{index}.py"},
                    )
                )
            aggregator.flush()

            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(lines), 2)
        self.assertEqual([line["event_type"] for line in lines], ["physical_write", "physical_write"])
        self.assertTrue(all(line["capture_mode"] == "full" for line in lines))

    def test_trace_aggregator_flushes_pending_aggregates_before_critical_event(self):
        from onecode.kernel.trace import TraceAggregator, TraceEvent

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            aggregator = TraceAggregator(path)

            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="progress-1",
                    parent_span_id=None,
                    event_type="progress_tick",
                    status="observed",
                    payload={"completed_count": 1},
                    timestamp="2026-06-02T00:00:00+00:00",
                )
            )
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="write-1",
                    parent_span_id=None,
                    event_type="physical_write",
                    status="completed",
                    payload={"path": "src/a.py"},
                    timestamp="2026-06-02T00:00:01+00:00",
                )
            )

            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([line["event_type"] for line in lines], ["progress_tick_aggregate", "physical_write"])
        self.assertEqual(lines[0]["capture_mode"], "aggregate")
        self.assertEqual(lines[1]["capture_mode"], "full")

    def test_trace_evidence_metrics_group_bytes_by_risk_and_capture_mode(self):
        from onecode.kernel.trace import TraceAggregator, TraceEvent, trace_evidence_metrics, write_trace_event

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            write_trace_event(
                path,
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="write-1",
                    parent_span_id=None,
                    event_type="physical_write",
                    status="completed",
                    payload={"path": "src/a.py"},
                ),
            )
            aggregator = TraceAggregator(path)
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="heartbeat-1",
                    parent_span_id=None,
                    event_type="heartbeat",
                    status="ok",
                    payload={"node": "local"},
                )
            )
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="heartbeat-2",
                    parent_span_id=None,
                    event_type="heartbeat",
                    status="ok",
                    payload={"node": "local"},
                )
            )
            aggregator.flush()

            metrics = trace_evidence_metrics(path)

        self.assertEqual(metrics["event_count"], 2)
        self.assertEqual(metrics["aggregate_event_count"], 1)
        self.assertEqual(metrics["events_by_risk_tier"]["critical"], 1)
        self.assertEqual(metrics["events_by_capture_mode"]["full"], 1)
        self.assertEqual(metrics["events_by_capture_mode"]["aggregate"], 1)
        self.assertGreater(metrics["bytes_by_risk_tier"]["critical"], 0)
        self.assertGreater(metrics["bytes_by_capture_mode"]["aggregate"], 0)

    def test_trace_evidence_metrics_include_write_latency_summary(self):
        from onecode.kernel.trace import TraceEvent, trace_evidence_metrics, write_trace_event

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            write_trace_event(
                path,
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="write-1",
                    parent_span_id=None,
                    event_type="physical_write",
                    status="completed",
                    payload={"path": "src/a.py"},
                ),
            )

            metrics = trace_evidence_metrics(path)

        self.assertIn("write_latency_ms", metrics)
        self.assertEqual(metrics["write_latency_ms"]["count"], 1)
        self.assertGreaterEqual(metrics["write_latency_ms"]["max"], 0)
        self.assertGreaterEqual(metrics["write_latency_ms"]["p95"], 0)

    def test_trace_evidence_metrics_identify_aggregate_window_gaps(self):
        from onecode.kernel.trace import TraceAggregator, TraceEvent, trace_evidence_metrics

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            aggregator = TraceAggregator(path)
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="progress-1",
                    parent_span_id=None,
                    event_type="progress_tick",
                    status="observed",
                    payload={"completed_count": 1},
                    timestamp="2026-06-02T00:00:00+00:00",
                )
            )
            aggregator.flush()
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="progress-2",
                    parent_span_id=None,
                    event_type="progress_tick",
                    status="observed",
                    payload={"completed_count": 2},
                    timestamp="2026-06-02T00:10:00+00:00",
                )
            )
            aggregator.flush()

            metrics = trace_evidence_metrics(path, aggregate_gap_threshold_seconds=300)

        self.assertEqual(metrics["aggregate_gap_count"], 1)
        self.assertEqual(metrics["max_aggregate_gap_seconds"], 600.0)

    def test_trace_evidence_metrics_detects_cross_type_aggregate_gaps_by_timestamp(self):
        from onecode.kernel.trace import TraceAggregator, TraceEvent, trace_evidence_metrics

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            aggregator = TraceAggregator(path)
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="progress-1",
                    parent_span_id=None,
                    event_type="progress_tick",
                    status="observed",
                    payload={"completed_count": 1},
                    timestamp="2026-06-02T00:00:00+00:00",
                )
            )
            aggregator.record(
                TraceEvent(
                    trace_id="trace-1",
                    run_id="run-1",
                    span_id="heartbeat-1",
                    parent_span_id=None,
                    event_type="heartbeat",
                    status="ok",
                    payload={"node": "local"},
                    timestamp="2026-06-02T00:10:00+00:00",
                )
            )
            aggregator.flush()

            metrics = trace_evidence_metrics(path, aggregate_gap_threshold_seconds=300)

        self.assertEqual(metrics["aggregate_gap_count"], 1)
        self.assertEqual(metrics["max_aggregate_gap_seconds"], 600.0)

    def test_trace_event_escalates_failed_medium_event_to_high_compact(self):
        from onecode.kernel.trace import TraceEvent

        event = TraceEvent(
            trace_id="trace-1",
            run_id="run-1",
            span_id="tool-1",
            parent_span_id="run",
            event_type="tool_call_completed",
            status="halted",
            payload={"reason": "http_timeout"},
        )

        payload = event.to_dict()
        self.assertEqual(payload["risk_tier"], "high")
        self.assertEqual(payload["capture_mode"], "compact")
        self.assertEqual(payload["classification_reason"], "anomaly_escalation")
