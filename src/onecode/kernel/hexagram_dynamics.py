from __future__ import annotations

import math



from typing import ClassVar, Any, Protocol, cast

class TransitionRecord(Protocol):
    status_code: int
    action: str
    reason: str

class IchingDynamicsMixin:
    POLARITY_THRESHOLD: ClassVar[float]
    ELEMENT_ORDER: ClassVar[Any]
    ELEMENT_DAMPING_ALPHA: ClassVar[float]
    ELEMENT_EXECUTION_BANDWIDTH: ClassVar[dict[tuple[str, str], float]]
    ENTROPY_THRESHOLD: ClassVar[float]
    ROLLBACK_STATUS: ClassVar[int]

    @classmethod
    def balance_mask(cls, status_code: int, threshold: float | None = None) -> int:
        polarity = cls.polarity_index(status_code)
        active_threshold = cls.POLARITY_THRESHOLD if threshold is None else threshold
        if abs(polarity) <= active_threshold:
            return 0b000000
        if polarity > active_threshold:
            return 0b100000
        return 0b000001
    @classmethod
    def apply_balanced_event(cls, status_code: int, event: str, threshold: float | None = None) -> int:
        normalized = status_code & 0b111111
        return normalized ^ cls.change_mask_for_event(normalized, event) ^ cls.balance_mask(normalized, threshold)
    @classmethod
    def evolved_element_labels(cls) -> list[str]:
        return [f"{element}+" for element in cls.ELEMENT_ORDER] + [f"{element}-" for element in cls.ELEMENT_ORDER]
    @classmethod
    def element_polarity(cls, trigram: int) -> str:
        profile = cls.yin_yang_profile_for_bits(trigram, width=3)
        from typing import cast
        return "+" if cast(int, profile["yang_count"]) >= cast(int, profile["yin_count"]) else "-"
    @classmethod
    def evolved_element_tensor(cls, status_code: int, alpha: float | None = None) -> list[list[float]]:
        polarity = cls.polarity_index(status_code)
        damping_alpha = cls.ELEMENT_DAMPING_ALPHA if alpha is None else alpha
        positive_to_negative = math.exp(damping_alpha * max(0.0, polarity))
        negative_to_positive = math.exp(damping_alpha * max(0.0, -polarity))
        tensor: list[list[float]] = []
        for source_label in cls.evolved_element_labels():
            source_element, source_polarity = source_label[:-1], source_label[-1]
            row = []
            for target_label in cls.evolved_element_labels():
                target_element, target_polarity = target_label[:-1], target_label[-1]
                coefficient = cls.ELEMENT_EXECUTION_BANDWIDTH[(source_element, target_element)]
                if source_polarity == "+" and target_polarity == "-":
                    coefficient *= positive_to_negative
                elif source_polarity == "-" and target_polarity == "+":
                    coefficient *= negative_to_positive
                row.append(coefficient)
            tensor.append(row)
        return tensor
    @classmethod
    def evolved_element_modulation(cls, status_code: int) -> dict[str, float | str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_label = f"{cls.element_for_trigram(outer)}{cls.element_polarity(outer)}"
        inner_label = f"{cls.element_for_trigram(inner)}{cls.element_polarity(inner)}"
        labels = cls.evolved_element_labels()
        tensor = cls.evolved_element_tensor(normalized)
        return {
            "outer_label": outer_label,
            "inner_label": inner_label,
            "coefficient": tensor[labels.index(outer_label)][labels.index(inner_label)],
            "polarity_index": cls.polarity_index(normalized),
        }
    @classmethod
    def global_entropy(cls, status_codes: list[int]) -> dict[str, float | str]:
        if not status_codes:
            return {"p1": 0.0, "p0": 1.0, "entropy": 0.0, "polarity_index": -1.0, "polarity_state": "low_entropy_negative"}
        total_bits = 6 * len(status_codes)
        yang_count = sum((status_code & 0b111111).bit_count() for status_code in status_codes)
        p1 = yang_count / total_bits
        p0 = 1 - p1
        polarity_index = (yang_count - (total_bits / 2)) / (total_bits / 2)

        def term(probability: float) -> float:
            return 0.0 if probability == 0.0 else probability * math.log2(probability)

        entropy = max(0.0, -(term(p0) + term(p1)))
        if entropy >= cls.ENTROPY_THRESHOLD:
            polarity_state = "entropy_balanced"
        elif polarity_index > 0:
            polarity_state = "low_entropy_positive"
        elif polarity_index < 0:
            polarity_state = "low_entropy_negative"
        else:
            polarity_state = "low_entropy_neutral"
        return {
            "p1": p1,
            "p0": p0,
            "entropy": entropy,
            "polarity_index": polarity_index,
            "polarity_state": polarity_state,
        }
    @classmethod
    def entropy_regulated_status(cls, status_codes: list[int]) -> dict[str, float | int | str]:
        entropy = cls.global_entropy(status_codes)
        if cast(float, entropy["entropy"]) < cls.ENTROPY_THRESHOLD:
            if cast(float, entropy["polarity_index"]) > 0:
                return {
                    "status_code": cls.aggregate_status(status_codes),
                    "decision": "accept_positive_polarity",
                    "entropy": entropy["entropy"],
                    "threshold": cls.ENTROPY_THRESHOLD,
                }
            return {
                "status_code": cls.ROLLBACK_STATUS,
                "decision": "rollback_negative_polarity",
                "reason": "entropy_negative_polarity_rollback",
                "entropy": entropy["entropy"],
                "threshold": cls.ENTROPY_THRESHOLD,
            }
        return {
            "status_code": cls.aggregate_status(status_codes),
            "decision": "accept",
            "entropy": entropy["entropy"],
            "threshold": cls.ENTROPY_THRESHOLD,
        }
    @classmethod
    def state_distribution_entropy(cls, status_codes: list[int]) -> dict[str, float | int | dict[int, float]]:
        if not status_codes:
            return {
                "entropy": 0.0,
                "max_entropy": 0.0,
                "unique_state_count": 0,
                "distribution": {},
                "kl_divergence_uniform": 0.0,
            }
        counts: dict[int, int] = {}
        for status_code in status_codes:
            normalized = status_code & 0b111111
            counts[normalized] = counts.get(normalized, 0) + 1
        total = len(status_codes)
        distribution = {status_code: count / total for status_code, count in sorted(counts.items())}
        entropy = -sum(probability * math.log2(probability) for probability in distribution.values())
        max_entropy = math.log2(len(distribution)) if distribution else 0.0
        kl_divergence = max(0.0, 6.0 - entropy)
        return {
            "entropy": entropy,
            "max_entropy": max_entropy,
            "unique_state_count": len(distribution),
            "distribution": distribution,
            "kl_divergence_uniform": kl_divergence,
        }
    @classmethod
    def kl_divergence_uniform(cls, status_codes: list[int]) -> float:
        """Calculate the Kullback-Leibler divergence D_KL(P || U_64) to the uniform prior on Q_6.

        D_KL(P || U_64) = log2(64) - H(P) = 6.0 - H(P)
        where H(P) is the empirical Shannon entropy in bits.
        Range: [0.0, 6.0] bits.
        - 0.0 bits: Perfectly uniform distribution across all 64 states.
        - 6.0 bits: Fully deterministic distribution on a single state (H = 0).
        """
        if not status_codes:
            return 0.0
        entropy_info = cls.state_distribution_entropy(status_codes)
        return cast(float, entropy_info["kl_divergence_uniform"])
    @classmethod
    def transition_graph(cls) -> dict[int, int]:
        return {
            status_code: cls.transition(status_code).status_code & 0b111111
            for status_code in range(64)
        }
    @classmethod
    def attractor_analysis(cls) -> dict[str, int | list[list[int]] | list[int]]:
        graph = cls.transition_graph()
        attractors: list[list[int]] = []
        classified: set[int] = set()
        seen_cycles: set[tuple[int, ...]] = set()
        for start in range(64):
            path: list[int] = []
            positions: dict[int, int] = {}
            current = start
            while current not in positions and current not in classified:
                positions[current] = len(path)
                path.append(current)
                current = graph[current]
            if current in positions:
                cycle = path[positions[current]:]
                canonical = min(tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle)))
                if canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    attractors.append(list(canonical))
            classified.update(path)
        return {
            "state_count": 64,
            "attractors": sorted(attractors, key=lambda cycle: (len(cycle), cycle)),
            "unclassified_states": sorted(set(range(64)) - classified),
        }
    @classmethod
    def stability_analysis(cls) -> dict[str, int | float | dict[int, int]]:
        graph = cls.transition_graph()
        attractors = cls.attractor_analysis()
        steps_to_attractor: dict[int, int] = {}
        for start in range(64):
            current = start
            seen: dict[int, int] = {}
            steps = 0
            while current not in seen:
                seen[current] = steps
                next_state = graph[current]
                if next_state == current:
                    steps_to_attractor[start] = steps
                    break
                current = next_state
                steps += 1
            else:
                steps_to_attractor[start] = seen[current]
            if start not in steps_to_attractor:
                steps_to_attractor[start] = steps

        energy_deltas = [
            cls.lyapunov_energy(graph[status_code]) - cls.lyapunov_energy(status_code)
            for status_code in range(64)
        ]
        return {
            "state_count": 64,
            "limit_cycle_count": len(cast(list[list[int]], attractors["attractors"])),
            "nontrivial_limit_cycle_count": sum(1 for cycle in cast(list[list[int]], attractors["attractors"]) if len(cycle) > 1),
            "unclassified_state_count": len(cast(list[int], attractors["unclassified_states"])),
            "steps_to_attractor": steps_to_attractor,
            "max_steps_to_attractor": max(steps_to_attractor.values()) if steps_to_attractor else 0,
            "energy_increase_transition_count": sum(1 for delta in energy_deltas if delta > 0),
            "energy_decrease_transition_count": sum(1 for delta in energy_deltas if delta < 0),
            "energy_flat_transition_count": sum(1 for delta in energy_deltas if delta == 0),
            "min_energy_delta": min(energy_deltas) if energy_deltas else 0.0,
            "max_energy_delta": max(energy_deltas) if energy_deltas else 0.0,
        }
    @staticmethod
    def hamming_distance(left: int, right: int) -> int:
        return ((left ^ right) & 0b111111).bit_count()
    @classmethod
    def topology_certificate(cls) -> dict[str, int | str | dict[int, int]]:
        graph = cls.transition_graph()
        distance_histogram = {distance: 0 for distance in range(7)}
        closed_transition_count = 0
        fixed_point_count = 0
        hypercube_edge_transition_count = 0
        long_jump_transition_count = 0
        for source, target in graph.items():
            if 0 <= target < 64:
                closed_transition_count += 1
            distance = cls.hamming_distance(source, target)
            distance_histogram[distance] += 1
            if distance == 0:
                fixed_point_count += 1
            elif distance == 1:
                hypercube_edge_transition_count += 1
            else:
                long_jump_transition_count += 1
        return {
            "state_space": "Q6",
            "vertex_count": 64,
            "dimension": 6,
            "hypercube_edge_count": 6 * (2 ** 5),
            "transition_count": len(graph),
            "closed_transition_count": closed_transition_count,
            "unclosed_transition_count": len(graph) - closed_transition_count,
            "fixed_point_count": fixed_point_count,
            "hypercube_edge_transition_count": hypercube_edge_transition_count,
            "long_jump_transition_count": long_jump_transition_count,
            "hamming_distance_histogram": distance_histogram,
        }
    @classmethod
    def lyapunov_certificate(cls) -> dict[str, bool | int | float | list[dict[str, float | int]]]:
        graph = cls.transition_graph()
        deltas: list[float] = []
        violating_transitions: list[dict[str, float | int]] = []
        for source, target in graph.items():
            source_energy = cls.lyapunov_energy(source)
            target_energy = cls.lyapunov_energy(target)
            delta = target_energy - source_energy
            deltas.append(delta)
            if delta > 0:
                violating_transitions.append(
                    {
                        "source": source,
                        "target": target,
                        "source_energy": source_energy,
                        "target_energy": target_energy,
                        "delta": delta,
                    }
                )
        return {
            "state_count": len(graph),
            "nonincreasing": not violating_transitions,
            "energy_increase_transition_count": len(violating_transitions),
            "energy_decrease_transition_count": sum(1 for delta in deltas if delta < 0),
            "energy_flat_transition_count": sum(1 for delta in deltas if delta == 0),
            "min_energy_delta": min(deltas) if deltas else 0.0,
            "max_energy_delta": max(deltas) if deltas else 0.0,
            "violating_transitions": violating_transitions,
        }
    @classmethod
    def entropy_gate_certificate(cls, status_codes: list[int]) -> dict[str, float | int | str]:
        distribution = cls.state_distribution_entropy(status_codes)
        max_entropy = cast(float, distribution["max_entropy"])
        entropy = cast(float, distribution["entropy"])
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        sample_count = len(status_codes)
        unique_state_count = cast(int, distribution["unique_state_count"])
        transition_actions = [
            cls.transition(status_code).action
            for status_code in status_codes
        ]
        halt_count = sum(1 for action in transition_actions if action == "halt")
        checkpoint_count = sum(1 for action in transition_actions if action == "checkpoint")
        if sample_count == 0:
            decision = "observe"
            reason = "empty_sequence"
        elif normalized_entropy <= cls.ENTROPY_THRESHOLD and halt_count > 0:
            decision = "sovereignty_halt"
            reason = "low_entropy_repeated_halt"
        elif normalized_entropy <= cls.ENTROPY_THRESHOLD and checkpoint_count > 0:
            decision = "checkpoint"
            reason = "low_entropy_repeated_checkpoint"
        elif normalized_entropy > cls.ENTROPY_THRESHOLD:
            decision = "observe"
            reason = "high_entropy_exploration"
        else:
            decision = "continue"
            reason = "low_entropy_stable"
        return {
            "sample_count": sample_count,
            "unique_state_count": unique_state_count,
            "entropy": entropy,
            "max_entropy": max_entropy,
            "normalized_entropy": normalized_entropy,
            "threshold": cls.ENTROPY_THRESHOLD,
            "halt_count": halt_count,
            "checkpoint_count": checkpoint_count,
            "decision": decision,
            "reason": reason,
        }
    @classmethod
    def totality_samples(cls) -> list[dict[str, str | bool | None]]:
        return [
            {"kind": "runtime", "status": "completed", "reason": None, "dangerous": False},
            {"kind": "runtime", "status": "skipped", "reason": "resumed_asset_ready", "dangerous": False},
            {"kind": "runtime", "status": "halted", "reason": "sovereignty_breach", "dangerous": True},
            {"kind": "runtime", "status": "denied", "reason": "permission_denied", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "invalid_intent", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "self_audit_check_failed", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "http_timeout", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "action_exception", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "run_exception", "dangerous": True},
            {"kind": "runtime", "status": "unknown", "reason": "malformed_input", "dangerous": True},
            {"kind": "runtime", "status": "unknown", "reason": "oversized_input", "dangerous": True},
            {"kind": "runtime", "status": "halted", "reason": "resource_budget_exceeded", "dangerous": True},
            {"kind": "resume", "status": "ready", "reason": None, "dangerous": False},
            {"kind": "resume", "status": "ignored", "reason": "path_outside_workspace", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "missing_file", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "sha256_mismatch", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "malformed_manifest", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "invalid_checkpoint_evidence", "dangerous": True},
            {"kind": "resume", "status": "ignored", "reason": "checkpoint_sha_mismatch", "dangerous": True},
        ]
    @classmethod
    def classify_known_input(cls, sample: dict[str, str | bool | None]) -> int:
        kind = sample["kind"]
        status = str(sample["status"])
        reason = sample["reason"]
        reason_value = str(reason) if reason is not None else None
        if kind == "resume":
            return cls.classify_resume_audit(status, reason_value)
        return cls.classify_outcome(status, reason_value)
    @classmethod
    def totality_certificate(cls) -> dict[str, bool | int | str | list[str]]:
        samples = cls.totality_samples()
        mapped = [cls.classify_known_input(sample) for sample in samples]
        unmapped_count = sum(1 for status_code in mapped if not 0 <= status_code < 64)
        return {
            "domain": "known_runtime_and_resume_inputs",
            "codomain": "Q6",
            "sample_count": len(samples),
            "mapped_count": len(mapped) - unmapped_count,
            "unmapped_count": unmapped_count,
            "total_over_known_inputs": unmapped_count == 0,
            "safe_domain": ["halt", "checkpoint", "discover"],
        }
    @classmethod
    def safety_dominance_certificate(cls) -> dict[str, bool | int | list[dict[str, int | str | bool | None]] | dict[str, int]]:
        unsafe_pass_through_samples: list[dict[str, int | str | bool | None]] = []
        histogram: dict[str, int] = {}
        dangerous_sample_count = 0
        for sample in cls.totality_samples():
            if not bool(sample["dangerous"]):
                continue
            dangerous_sample_count += 1
            status_code = cls.classify_known_input(sample)
            transition = cls.transition(status_code)
            histogram[transition.action] = histogram.get(transition.action, 0) + 1
            if transition.action in {"continue", "accelerate", "activate"}:
                unsafe_pass_through_samples.append(
                    {
                        "kind": sample["kind"],
                        "status": sample["status"],
                        "reason": sample["reason"],
                        "status_code": status_code,
                        "transition_action": transition.action,
                        "transition_reason": transition.reason,
                    }
                )
        return {
            "dangerous_sample_count": dangerous_sample_count,
            "dangerous_action_histogram": histogram,
            "unsafe_pass_through_count": len(unsafe_pass_through_samples),
            "unsafe_pass_through_samples": unsafe_pass_through_samples,
            "safe": not unsafe_pass_through_samples,
        }
    @classmethod
    def collision_risk_certificate(cls) -> dict[str, bool | int | list[dict[str, int | str | list[str]]]]:
        grouped: dict[int, list[dict[str, str | bool | None]]] = {}
        for sample in cls.totality_samples():
            status_code = cls.classify_known_input(sample)
            grouped.setdefault(status_code, []).append(sample)
        unsafe_collisions: list[dict[str, int | str | list[str]]] = []
        for status_code, samples in grouped.items():
            if len(samples) < 2:
                continue
            has_dangerous = any(bool(sample["dangerous"]) for sample in samples)
            has_nondangerous = any(not bool(sample["dangerous"]) for sample in samples)
            transition = cls.transition(status_code)
            if has_dangerous and has_nondangerous and transition.action in {"continue", "accelerate", "activate"}:
                unsafe_collisions.append(
                    {
                        "status_code": status_code,
                        "transition_action": transition.action,
                        "sample_reasons": [
                            str(sample["reason"]) if sample["reason"] is not None else str(sample["status"])
                            for sample in samples
                        ],
                    }
                )
        return {
            "sample_count": len(cls.totality_samples()),
            "collision_state_count": sum(1 for samples in grouped.values() if len(samples) > 1),
            "unsafe_collision_count": len(unsafe_collisions),
            "unsafe_collisions": unsafe_collisions,
            "safe": not unsafe_collisions,
        }
