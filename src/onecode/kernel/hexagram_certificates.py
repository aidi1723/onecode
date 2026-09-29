from __future__ import annotations


from onecode.kernel.iching_encoding import ACTIVE_RULE_SCHEMA


class IchingCertificatesMixin:
    @classmethod
    def lyapunov_energy(cls, status_code: int) -> float:
        normalized = status_code & 0b111111
        profile = cls.yin_yang_profile(normalized)
        balance_penalty = abs(float(profile["yang_count"]) - 3.0) / 3.0
        transition = cls.transition(normalized)
        action_penalties = {
            "continue": 0.0,
            "recover": 0.0,
            "accelerate": 0.1,
            "activate": 0.2,
            "cooldown": 0.35,
            "throttle": 0.45,
            "prune": 0.55,
            "checkpoint": 0.75,
            "discover": 0.85,
            "halt": 1.0,
        }
        bandwidth_penalty = 1.0 - cls.execution_bandwidth(normalized)
        return balance_penalty + action_penalties.get(transition.action, 0.5) + bandwidth_penalty
    @classmethod
    def hysteresis_gate(cls, value: float, previous: int, low: float, high: float) -> int:
        if low >= high:
            raise ValueError("low must be less than high")
        previous_bit = 1 if previous else 0
        if value <= low:
            return 0
        if value >= high:
            return 1
        return previous_bit
    @classmethod
    def element_dynamics(cls, status_code: int) -> dict[str, str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        relation = cls.element_relation(outer_element, inner_element)
        cross_relation = cls.element_cross_relation(outer_element, inner_element)
        pressure = cls.yin_yang_cross_profile(normalized)["pressure"]
        if cross_relation == "controls" and outer_element == "fire" and inner_element == "metal":
            modulation = "hard_control"
        elif cross_relation == "generates" and outer_element == "water" and inner_element == "wood":
            modulation = "recovery_seed"
        elif cross_relation == "controls" and outer_element == "water" and inner_element == "fire":
            modulation = "quench"
        elif cross_relation == "controls" and outer_element == "metal" and inner_element == "wood":
            modulation = "prune"
        elif cross_relation == "generates" and outer_element == "wood" and inner_element == "fire":
            modulation = "fuel"
        elif cross_relation == "controls" and outer_element == "earth" and inner_element == "water":
            modulation = "dam"
        elif cross_relation == "controls" and outer_element == "wood" and inner_element == "earth":
            modulation = "break_ground"
        else:
            modulation = "normal"
        return {
            "outer_element": outer_element,
            "inner_element": inner_element,
            "relation": relation,
            "cross_relation": cross_relation,
            "yin_yang_pressure": str(pressure),
            "modulation": modulation,
        }
    @classmethod
    def cross_cutting_profile(cls, status_code: int) -> dict:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        dynamics = cls.element_dynamics(normalized)
        transition = cls.transition(normalized)
        runtime_action, runtime_reason = cls.runtime_relation_policy(dynamics["cross_relation"], dynamics["modulation"])
        if dynamics["modulation"] == "recovery_seed" and transition.action == "checkpoint":
            runtime_action, runtime_reason = transition.action, transition.reason
        dispatch_decision = cls.dispatch_decision(transition)
        return {
            "rule_schema": ACTIVE_RULE_SCHEMA,
            "status_code": normalized,
            "binary": format(normalized, "06b"),
            "math": {
                "liangyi": list(cls.liangyi_values()),
                "state_space_sizes": {
                    "liangyi": 1 << 1,
                    "sixiang": 1 << 2,
                    "bagua": 1 << 3,
                    "hexagram": 1 << 6,
                },
            },
            "dimension": cls.dimension_profile(6),
            "triadic": cls.triadic_profile(normalized),
            "position": cls.line_position_profile(normalized),
            "correspondence": cls.correspondence_profile(normalized),
            "perspective": cls.perspective_profile(normalized),
            "mutation": None,
            "nuclear": cls.nuclear_profile(normalized),
            "outer_trigram": outer,
            "inner_trigram": inner,
            "lines": cls.line_records(normalized),
            "liangyi": cls.liangyi_bits(normalized),
            "outer_trigram_record": cls.trigram_record(normalized, "outer"),
            "inner_trigram_record": cls.trigram_record(normalized, "inner"),
            "outer_trigram_virtue": cls.trigram_virtue_record(outer),
            "inner_trigram_virtue": cls.trigram_virtue_record(inner),
            "trigram_records": cls.trigram_records(),
            "outer_element": outer_element,
            "inner_element": inner_element,
            "element_records": cls.element_records(),
            "element_matrix": {f"{source}->{target}": relation for (source, target), relation in cls.element_matrix().items()},
            "element_relation": cls.element_relation(outer_element, inner_element),
            "element_dynamics": dynamics,
            "runtime_policy": {
                "action": runtime_action,
                "reason": runtime_reason,
            },
            "execution_bandwidth": cls.execution_bandwidth(normalized),
            "evolved_element_modulation": cls.evolved_element_modulation(normalized),
            "harmony": cls.harmony_score(normalized),
            "yin_yang": cls.yin_yang_cross_profile(normalized),
            "four_symbols": cls.four_symbols(normalized),
            "overlapping_four_symbols": cls.overlapping_four_symbols(normalized),
            "four_symbol_balance": cls.four_symbol_balance_vector(normalized),
            "transition": {
                "status_code": transition.status_code,
                "action": transition.action,
                "reason": transition.reason,
            },
            "dispatch_decision": dispatch_decision,
            "rule_layers": cls.rule_layers(),
        }
    @classmethod
    def hexagram_record(cls, status_code: int) -> dict:
        return cls.cross_cutting_profile(status_code)
    @classmethod
    def hexagram_records(cls) -> dict[int, dict]:
        return {status_code: cls.hexagram_record(status_code) for status_code in range(64)}
    @classmethod
    def flip_line(cls, status_code: int, line_index: int) -> int:
        if line_index < 0 or line_index > 5:
            raise ValueError(f"line_index must be between 0 and 5: {line_index!r}")
        return (status_code & 0b111111) ^ (1 << line_index)
    @classmethod
    def mutate_lines(cls, status_code: int, line_indexes) -> int:
        normalized = status_code & 0b111111
        mask = 0
        for line_index in sorted(set(line_indexes)):
            if line_index < 0 or line_index > 5:
                raise ValueError(f"line_index must be between 0 and 5: {line_index!r}")
            mask |= 1 << line_index
        return normalized ^ mask
    @classmethod
    def changed_lines(cls, before: int, after: int) -> list[int]:
        change_mask = (before ^ after) & 0b111111
        return [line_index for line_index in range(6) if change_mask & (1 << line_index)]
    @classmethod
    def mutation_profile(cls, before: int, after: int) -> dict[str, int | list[int] | list[str]]:
        normalized_before = before & 0b111111
        normalized_after = after & 0b111111
        changed = cls.changed_lines(normalized_before, normalized_after)
        changed_bands = [
            name
            for name, _role, line_indexes in cls.TRIADIC_BANDS
            if any(line_index in line_indexes for line_index in changed)
        ]
        return {
            "before": normalized_before,
            "after": normalized_after,
            "changed_lines": changed,
            "change_count": len(changed),
            "changed_bands": changed_bands,
        }
    @classmethod
    def balance_mutation_evidence(cls, before: int, after: int) -> dict[str, object]:
        normalized_before = before & 0b111111
        normalized_after = after & 0b111111
        before_profile = cls.cross_cutting_profile(normalized_before)
        after_profile = cls.cross_cutting_profile(normalized_after)

        def state_evidence(profile: dict[str, object]) -> dict[str, object]:
            return {
                "status_code": profile["status_code"],
                "binary": profile["binary"],
                "yin_yang": profile["yin_yang"],
                "inner_element": profile["inner_element"],
                "outer_element": profile["outer_element"],
                "element_dynamics": profile["element_dynamics"],
                "transition": profile["transition"],
                "dispatch_decision": profile["dispatch_decision"],
            }

        return {
            "rule_schema": ACTIVE_RULE_SCHEMA,
            "mutation": cls.mutation_profile(normalized_before, normalized_after),
            "before": state_evidence(before_profile),
            "after": state_evidence(after_profile),
        }
    @classmethod
    def nuclear_hexagram(cls, status_code: int) -> int:
        bits = cls.bits_for_state(status_code & 0b111111, width=6)
        return cls.state_for_bits([bits[1], bits[2], bits[3], bits[2], bits[3], bits[4]])
    @classmethod
    def nuclear_profile(cls, status_code: int) -> dict[str, int | str]:
        nuclear = cls.nuclear_hexagram(status_code)
        inner = nuclear & 0b111
        outer = (nuclear >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        transition = cls.transition(nuclear)
        return {
            "status_code": nuclear,
            "binary": format(nuclear, "06b"),
            "inner_trigram": inner,
            "outer_trigram": outer,
            "outer_element": outer_element,
            "inner_element": inner_element,
            "element_relation": cls.element_cross_relation(outer_element, inner_element),
            "transition_action": transition.action,
            "transition_reason": transition.reason,
        }
    @classmethod
    def nuclear_chain(cls, status_code: int, max_steps: int = 4) -> list[int]:
        """Generate the iterated nuclear hexagram sequence starting from status_code."""
        chain = [status_code & 0b111111]
        for _ in range(max_steps):
            nxt = cls.nuclear_hexagram(chain[-1])
            chain.append(nxt)
            if len(chain) >= 2 and nxt == chain[-2]:
                break
        return chain
    @classmethod
    def nuclear_attractor(cls, status_code: int) -> dict[str, object]:
        """Analyze the attractor of the iterated nuclear hexagram mapping.

        Mathematical Theorem:
        Every hexagram S in Q_6 converges in at most 2 iterations of nuclear_hexagram
        to one of the four cardinal attractors:
        - Fixed points: 0 (Kun 坤) or 63 (Qian 乾)
        - 2-cycle: {21 (Wei Ji 未济), 42 (Ji Ji 既济)}
        """
        chain = [status_code & 0b111111]
        seen = {chain[0]: 0}
        current = chain[0]
        while True:
            nxt = cls.nuclear_hexagram(current)
            if nxt in seen:
                cycle_start = seen[nxt]
                cycle = chain[cycle_start:]
                break
            seen[nxt] = len(chain)
            chain.append(nxt)
            current = nxt

        attractor_type = "fixed_point" if len(cycle) == 1 else "limit_cycle"
        return {
            "initial_status_code": status_code & 0b111111,
            "chain": chain,
            "steps_to_attractor": cycle_start,
            "attractor": cycle,
            "attractor_type": attractor_type,
        }
    @classmethod
    def opposite_hexagram(cls, status_code: int) -> int:
        return (status_code & 0b111111) ^ 0b111111
    @classmethod
    def inverse_hexagram(cls, status_code: int) -> int:
        bits = cls.bits_for_state(status_code & 0b111111, width=6)
        return cls.state_for_bits(list(reversed(bits)))
    @classmethod
    def exchange_hexagram(cls, status_code: int) -> int:
        """Trigram exchange operator (交卦 / 上下易位).

        Swaps the outer (upper) and inner (lower) trigrams.
        This forms the fourth cardinal hexagram involution alongside
        opposite (错卦) and inverse (综卦).
        """
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        return (inner << 3) | outer
    @classmethod
    def perspective_profile(cls, status_code: int) -> dict[str, int | str]:
        normalized = status_code & 0b111111
        opposite = cls.opposite_hexagram(normalized)
        inverse = cls.inverse_hexagram(normalized)
        exchange = cls.exchange_hexagram(normalized)
        return {
            "status_code": normalized,
            "opposite_status_code": opposite,
            "opposite_binary": format(opposite, "06b"),
            "inverse_status_code": inverse,
            "inverse_binary": format(inverse, "06b"),
            "exchange_status_code": exchange,
            "exchange_binary": format(exchange, "06b"),
        }
    @classmethod
    def target_status_for_event(cls, event: str) -> int:
        if event in {"completed", "write_completed", "patch_completed"}:
            return cls.compute_status(cls.QIAN, cls.QIAN)
        if event in {"skipped", "resumed_asset_ready"}:
            return cls.compute_status(cls.QIAN, cls.DUI)
        if event in {"http_timeout", "network_timeout"}:
            return cls.compute_status(cls.KAN, cls.ZHEN)
        if event in {"action_exception", "run_exception", "local_executor_fault"}:
            return cls.compute_status(cls.GEN, cls.KUN)
        if event in {"sovereignty_breach", "permission_denied", "invalid_intent"}:
            return cls.compute_status(cls.LI, cls.KUN)
        return cls.compute_status(cls.KUN, cls.KUN)
    @classmethod
    def change_mask_for_event(cls, status_code: int, event: str) -> int:
        return (status_code & 0b111111) ^ cls.target_status_for_event(event)
    @classmethod
    def apply_event(cls, status_code: int, event: str) -> int:
        return (status_code & 0b111111) ^ cls.change_mask_for_event(status_code, event)
