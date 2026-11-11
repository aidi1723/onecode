"""Prometheus and OpenMetrics text format exporter for OneCode enterprise observability.

Exposes standard metrics for scrapers (Prometheus, Grafana Agent, Datadog):
- onecode_up (gauge)
- onecode_info (gauge with version and parity metadata)
- onecode_process_resident_memory_bytes (gauge)
- onecode_wal_entries_total (counter by risk tier and capture mode)
- onecode_wal_bytes_total (counter)
- onecode_runs_total (counter by status)
- onecode_hexagram_outcomes_total (counter by hexagram status code)
"""
from __future__ import annotations

import resource
import sys
from pathlib import Path
from typing import Any

from onecode.kernel.run_inspection import list_runs
from onecode.kernel.wal import global_wal_metrics_summary
from onecode.web.workspace import workspace_from_value


def _format_metric_header(name: str, doc: str, metric_type: str) -> list[str]:
    return [
        f"# HELP {name} {doc}",
        f"# TYPE {name} {metric_type}",
    ]


def _format_labels(labels: dict[str, Any]) -> str:
    if not labels:
        return ""
    pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return "{" + ",".join(pairs) + "}"


def _get_process_rss_bytes() -> int:
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            return int(usage.ru_maxrss)
        return int(usage.ru_maxrss) * 1024
    except Exception:
        return 0


def collect_prometheus_metrics(workspace_path: Path | str | None = None) -> list[str]:
    lines: list[str] = []

    # 1. onecode_up
    lines.extend(_format_metric_header("onecode_up", "Whether the OneCode service is operational.", "gauge"))
    lines.append("onecode_up 1")

    # 2. onecode_info
    lines.extend(_format_metric_header("onecode_info", "Build and version metadata for OneCode.", "gauge"))
    lines.append('onecode_info{claims_mainstream_parity="false",service="onecode",version="1.1.0"} 1')

    # 3. onecode_process_resident_memory_bytes
    rss = _get_process_rss_bytes()
    lines.extend(_format_metric_header("onecode_process_resident_memory_bytes", "Resident set size in bytes.", "gauge"))
    lines.append(f"onecode_process_resident_memory_bytes {rss}")

    ws: Path | None = None
    if isinstance(workspace_path, Path):
        ws = workspace_path.resolve() if workspace_path.is_dir() else None
    elif isinstance(workspace_path, str) and workspace_path.strip():
        try:
            ws = workspace_from_value(workspace_path)
        except Exception:
            candidate = Path(workspace_path).expanduser().resolve()
            if candidate.is_dir():
                ws = candidate
    else:
        try:
            ws = workspace_from_value(None)
        except Exception:
            pass

    if ws is not None:
        # 4. WAL metrics
        try:
            wal = global_wal_metrics_summary(ws)
            entries_by_rt = wal.get("entries_by_risk_tier", {})
            if entries_by_rt:
                lines.extend(_format_metric_header("onecode_wal_entries_total", "Total WAL log entries committed.", "counter"))
                for rt, count in sorted(entries_by_rt.items()):
                    lines.append(f'onecode_wal_entries_total{_format_labels({"risk_tier": rt})} {count}')

            bytes_by_rt = wal.get("bytes_by_risk_tier", {})
            if bytes_by_rt:
                lines.extend(_format_metric_header("onecode_wal_bytes_total", "Total bytes written to WAL.", "counter"))
                for rt, b_count in sorted(bytes_by_rt.items()):
                    lines.append(f'onecode_wal_bytes_total{_format_labels({"risk_tier": rt})} {b_count}')
        except Exception:
            pass

        # 5. Run & Hexagram Metrics
        try:
            runs_data = list_runs(ws)
            runs = runs_data.get("runs", [])
            status_counts: dict[str, int] = {}
            hex_counts: dict[int, int] = {}
            for r in runs:
                status = str(r.get("status") or "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                hex_code = r.get("iching_status_code") or r.get("outcome_status_code")
                if isinstance(hex_code, int):
                    hex_counts[hex_code] = hex_counts.get(hex_code, 0) + 1

            if status_counts:
                lines.extend(_format_metric_header("onecode_runs_total", "Total recorded agent exploration runs.", "counter"))
                for st, cnt in sorted(status_counts.items()):
                    lines.append(f'onecode_runs_total{_format_labels({"status": st})} {cnt}')

            if hex_counts:
                lines.extend(_format_metric_header("onecode_hexagram_outcomes_total", "Recorded hexagram terminal outcome codes.", "counter"))
                for h_code, cnt in sorted(hex_counts.items()):
                    lines.append(f'onecode_hexagram_outcomes_total{_format_labels({"hexagram_code": str(h_code)})} {cnt}')
        except Exception:
            pass

    return lines


def format_prometheus_metrics(workspace_path: Path | str | None = None) -> bytes:
    """Renders Prometheus metrics as UTF-8 encoded text lines."""
    lines = collect_prometheus_metrics(workspace_path)
    return ("\n".join(lines) + "\n").encode("utf-8")
