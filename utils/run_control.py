"""Shared cooperative cancellation support for migration agent runs."""

from threading import Event


class RunCancelledError(Exception):
    """Raised when an agent run is cancelled between work units."""


def raise_if_cancelled(stop_event: Event | None) -> None:
    if stop_event is not None and stop_event.is_set():
        raise RunCancelledError("Run cancelled by the user.")
