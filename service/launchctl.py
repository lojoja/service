"""
service.launchctl

An interface for constructing and executing launchctl commands.
"""

from __future__ import annotations
import logging
import subprocess
import typing as t

if t.TYPE_CHECKING:
    from .service import Service


__all__ = ["DOMAIN_GUI", "DOMAIN_SYS", "boot", "change_state"]


DOMAIN_GUI = "gui"
DOMAIN_SYS = "system"

ERROR_GUI_ALREADY_STARTED = 5
ERROR_GUI_ALREADY_STOPPED = 5
ERROR_SIP = 150
ERROR_SYS_ALREADY_STARTED = 37
ERROR_SYS_ALREADY_STOPPED = 113


logger = logging.getLogger(__name__)


def _execute(subcommand: str, *args: str) -> None:
    """
    Construct and execute a launchctl command.

    Args:
        subcommand: The launchctl subcommand to run
        args: The arguments for the subcommand
    """
    cmd = ["launchctl", subcommand, *args]

    logger.debug('Calling launchctl with command "%s"', " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)


def boot(service: Service, run: bool = False) -> None:
    """Start or stop a service.

    Args:
        service: The service to modify.
        run: Whether to run (start) the service.

    Raises:
        RuntimeError: When the service is already in the target state, runtime state change is prevented by SIP, or
                      changing the runtime state fails.
    """
    subcmd, action, current_state = ("bootstrap", "start", "started") if run else ("bootout", "stop", "stopped")

    logger.debug("Changing service runtime state: %s (%s)", service.name, action)

    try:
        _execute(subcmd, service.domain, service.file)
    except subprocess.CalledProcessError as exc:
        if exc.returncode in [
            ERROR_GUI_ALREADY_STARTED,
            ERROR_GUI_ALREADY_STOPPED,
            ERROR_SYS_ALREADY_STARTED,
            ERROR_SYS_ALREADY_STOPPED,
        ]:
            msg = f"{service.name} is already {current_state}"
        else:
            reason = " due to SIP" if exc.returncode == ERROR_SIP else ""
            msg = f"Failed to {action} {service.name}{reason}"

        raise RuntimeError(msg) from exc


def change_state(service: Service, enable: bool = False) -> None:
    """Change service state (enable/disble).

    Args:
        service: The service to modify.
        enable: Whether the service should be enabled.

    Raises:
        ValueError: When an unknown service state is specified.
        RuntimeError: When the service state cannot be changed or failed to change.
    """
    subcmd = "enable" if enable else "disable"

    logger.debug("Changing service state: %s (%s)", service.name, subcmd)

    if service.domain != DOMAIN_SYS:
        raise RuntimeError(f'Cannot change service state in the "{service.domain}" domain')

    try:
        _execute(subcmd, service.id)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to {subcmd} {service.name}") from exc
