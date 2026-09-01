from __future__ import annotations

import argparse
import json
from pathlib import Path

from onecode.kernel.diagnostics import run_doctor
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.run_inspection import inspect_run, list_runs
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    shell_projection_schema,
)


READ_ONLY_COMMANDS = frozenset(
    {"inspect", "list-runs", "doctor", "math-audit", "shell-schema"}
)


def register_read_only_commands(subparsers: argparse._SubParsersAction) -> None:
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--workspace", default=".")
    inspect_parser.add_argument("--run-id", required=True)

    list_runs_parser = subparsers.add_parser("list-runs")
    list_runs_parser.add_argument("--workspace", default=".")

    subparsers.add_parser("doctor")
    subparsers.add_parser("math-audit")
    subparsers.add_parser("shell-schema")


def dispatch_read_only_command(args: argparse.Namespace) -> int | None:
    if args.subcommand == "inspect":
        exit_code, result = inspect_run(Path(args.workspace), args.run_id)
        print(json.dumps(attach_shell_projection(result), ensure_ascii=False, sort_keys=True))
        return exit_code

    if args.subcommand == "list-runs":
        result = list_runs(Path(args.workspace))
        print(json.dumps(attach_shell_projection_to_runs_payload(result), ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "doctor":
        result = run_doctor()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ok" else 1

    if args.subcommand == "math-audit":
        print(json.dumps(math_audit_payload(), ensure_ascii=False, sort_keys=True))
        return 0

    if args.subcommand == "shell-schema":
        print(json.dumps(shell_projection_schema(), ensure_ascii=False, sort_keys=True))
        return 0

    return None


def math_audit_payload() -> dict[str, object]:
    graph = IchingKernel.transition_graph()
    attractors = IchingKernel.attractor_analysis()
    stability = IchingKernel.stability_analysis()
    topology = IchingKernel.topology_certificate()
    lyapunov = IchingKernel.lyapunov_certificate()
    totality = IchingKernel.totality_certificate()
    safety_dominance = IchingKernel.safety_dominance_certificate()
    collision_risk = IchingKernel.collision_risk_certificate()
    entropy_gate = {
        "low_entropy_halt_probe": IchingKernel.entropy_gate_certificate(
            [
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
            ]
        ),
        "exploration_probe": IchingKernel.entropy_gate_certificate(
            [
                IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
                IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN),
                IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN),
            ]
        ),
    }
    energies = [IchingKernel.lyapunov_energy(status_code) for status_code in range(64)]
    return {
        "status": "ok",
        "state_count": len(graph),
        "transition_count": len(graph),
        "attractor_count": len(attractors["attractors"]),
        "attractors": attractors["attractors"],
        "unclassified_state_count": len(attractors["unclassified_states"]),
        "lyapunov_min": min(energies),
        "lyapunov_max": max(energies),
        "stability": stability,
        "topology": topology,
        "lyapunov": lyapunov,
        "entropy_gate": entropy_gate,
        "totality": totality,
        "safety_dominance": safety_dominance,
        "collision_risk": collision_risk,
        "accepted_mappings": [
            "transition_graph",
            "attractor_analysis",
            "stability_analysis",
            "topology_certificate",
            "lyapunov_certificate",
            "entropy_gate_certificate",
            "totality_certificate",
            "safety_dominance_certificate",
            "collision_risk_certificate",
            "lyapunov_energy",
            "state_distribution_entropy",
            "hysteresis_gate",
        ],
        "reference_only": [
            "probabilistic_sampling",
            "runtime_gain_learning",
            "multi_agent_tensor_product",
        ],
    }
