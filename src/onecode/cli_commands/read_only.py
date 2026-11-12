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
from onecode.kernel.symbolic_telemetry import (
    SYMBOLIC_EXTENSION_PACKAGE,
    call_symbolic_profile,
    symbolic_extension_loaded,
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

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--production", action="store_true", help="Require production deployment readiness")
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
        require_production = getattr(args, "production", False)
        result = run_doctor(require_production=require_production)
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
    core_mappings = [
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
    ]
    extended_mappings = [
        "ziwei_isomorphism_and_coupling",
        "shen_gong_subgroup_anchorage",
        "star_brightness_lyapunov_invariance",
        "jie_shen_even_subgroup_relief",
        "twelve_deities_triad_and_suipo",
        "flying_sihua_cascade",
        "triadic_synthesis",
        "ziwei_tianfu_and_yangtuo",
        "solar_equation_and_zishi",
        "school_divergence_consensus",
        "classical_patterns",
        "auxiliary_polarity_and_yunxian",
        "heming_synastry_and_noble_stars",
        "deep_computation_and_graph",
        "pathology_and_environmental",
        "six_channel_and_empty_palace",
        "doujun_and_solar_boundary",
        "auxiliary_pairs_and_city_solar",
        "changsheng_and_expanded_patterns",
        "ziwu_liuzhu_and_shengke",
        "dipper_axes_and_sha_po_lang",
        "ming_zhu_shen_zhu_and_void_stars",
        "pattern_breaking_and_resonance",
        "systemic_parameter_coupling",
        "iching_classical_correspondence",
    ]
    ziwei_audit = call_symbolic_profile(IchingKernel, "ziwei_mathematical_audit", force=True)
    payload: dict[str, object] = {
        "status": "ok",
        "state_count": len(graph),
        "transition_count": len(graph),
        "attractor_count": len(attractors["attractors"]),  # type: ignore
        "self_loop_fixed_point_count": sum(1 for src, dst in graph.items() if src == dst),
        "energy_decrease_transition_count": stability["energy_decrease_transition_count"],
        "attractors": attractors["attractors"],
        "unclassified_state_count": len(attractors["unclassified_states"]),  # type: ignore
        "lyapunov_min": min(energies),
        "lyapunov_max": max(energies),
        "stability": stability,
        "topology": topology,
        "lyapunov": lyapunov,
        "entropy_gate": entropy_gate,
        "totality": totality,
        "safety_dominance": safety_dominance,
        "collision_risk": collision_risk,
        "automaton_scope_note": (
            "64-state Q6 decision lookup table (56 self-loop fixed points, 8 energy-decreasing edges); "
            "runtime loop termination relies on explicit turn_budget and repeat-read guards."
        ),
        "symbolic_extension": {
            "package": SYMBOLIC_EXTENSION_PACKAGE,
            "installed": symbolic_extension_loaded(),
        },
        "accepted_mappings": core_mappings + (extended_mappings if ziwei_audit is not None else []),
        "reference_only": [
            "probabilistic_sampling",
            "runtime_gain_learning",
            "multi_agent_tensor_product",
        ],
    }
    if ziwei_audit is not None:
        payload["ziwei_audit"] = ziwei_audit
    return payload
