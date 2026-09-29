"""Runtime decisions used by the runner.

The hexagram code stays in the evidence record. These functions are the
explicit policy the runner calls.
"""

from onecode.kernel.hexagram import IchingKernel, IchingTransition


def ready_asset_should_skip() -> bool:
    status_code = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI)
    return IchingKernel.should_skip(status_code)


def transition_for_result(status: str, reason: str | None) -> IchingTransition:
    status_code = IchingKernel.classify_outcome(status, reason)
    return IchingKernel.transition(status_code)


def agent_cycle_decision(status: str, reason: str | None) -> dict[str, object]:
    """Interpret one tool outcome for the multi-turn agent cycle.

    The hexagram and dispatch values stay on the single-run rules. ``cycle``
    is the shell reading of that same transition: discover continues with
    read-only tools instead of ending the turn.
    """
    transition = transition_for_result(status, reason)
    dispatch = IchingKernel.dispatch_decision(transition)
    if transition.action == "halt":
        cycle = "stop"
    elif transition.action == "checkpoint":
        cycle = "verify"
    elif transition.action == "discover":
        cycle = "read_only_continue"
    elif dispatch == "continue":
        cycle = "model_continue"
    else:
        cycle = "stop"
    return {
        "status_code": transition.status_code,
        "transition_action": transition.action,
        "transition_reason": transition.reason,
        "dispatch": dispatch,
        "cycle": cycle,
    }
