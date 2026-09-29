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
