"""
service.cli

The command-line interface for service
"""

import logging
import os
from pathlib import Path
import platform
import typing as t

import click
from clickext import ClickextCommand, ClickextGroup, config_option, verbose_option

from . import launchctl
from .service import locate, Service


MACOS_MIN_VERSION = 12.0
CONFIG_FILE = Path(f'~{os.getenv("SUDO_USER", "")}/.config/service.toml').expanduser()


logger = logging.getLogger(__package__)


def get_reverse_domains(data: t.Optional[dict[str, list[str]]]) -> list[str]:
    """Build reverse domains from configuration file data.

    :param data: The parsed configuration file data.
    """
    if data is None or "reverse-domains" not in data:
        reverse_domains = []
    else:
        reverse_domains = data["reverse-domains"]

        if not isinstance(reverse_domains, list):
            logger.warning('Invalid configuration file. "reverse-domains" must be a list.')
            reverse_domains = []

    logger.debug("Configured with %s reverse domains", len(reverse_domains))

    return reverse_domains


def get_service(ctx: click.Context, param: click.Parameter, value: str) -> None:  # pylint: disable=unused-argument
    """Get the target service and store it on `ctx.obj`.

    :param ctx: The current click execution context.
    :param param: The parameter that triggered the callback.
    :param value: The parameter value.
    """
    reverse_domains: list[str] = ctx.obj.copy()
    ctx.obj = locate(value, reverse_domains)


@click.group(cls=ClickextGroup, global_opts=["config", "verbose"], shared_params=["name"])
@click.argument("name", nargs=1, callback=get_service, expose_value=False, type=click.STRING)
@click.version_option(package_name="py_service")
@config_option(CONFIG_FILE, processor=get_reverse_domains)
@verbose_option(logger)
def cli() -> None:
    """Extremely basic launchctl wrapper for macOS."""
    logger.debug("%s started", __package__)
    verify_platform()


@cli.command(cls=ClickextCommand)
@click.pass_obj
def disable(service: Service) -> None:
    """Disable a service (system domain only)."""
    launchctl.change_state(service, enable=False)
    logger.info("%s disabled", service.name)


@cli.command(cls=ClickextCommand)
@click.pass_obj
def enable(service: Service) -> None:
    """Enable a service (system domain only)."""
    launchctl.change_state(service, enable=True)
    logger.info("%s enabled", service.name)


@cli.command(cls=ClickextCommand)
@click.pass_obj
def restart(service: Service) -> None:
    """Restart a service."""
    launchctl.boot(service, run=False)
    launchctl.boot(service, run=True)
    logger.info("%s restarted", service.name)


@cli.command(cls=ClickextCommand)
@click.option(
    "--enable",
    "-e",
    "enable_service",
    is_flag=True,
    default=False,
    help="Enable sevice before starting (system domain only).",
)
@click.pass_obj
def start(service: Service, enable_service: bool) -> None:
    """Start a service."""
    if enable_service:
        launchctl.change_state(service, enable=True)

    launchctl.boot(service, run=True)
    logger.info("%s %sstarted", service.name, "enabled and " if enable_service else "")


@cli.command(cls=ClickextCommand)
@click.option(
    "--disable",
    "-d",
    "disable_service",
    is_flag=True,
    default=False,
    help="Disable service after stopping (system domain only).",
)
@click.pass_obj
def stop(service: Service, disable_service: bool) -> None:
    """Stop a service."""
    launchctl.boot(service, run=False)

    if disable_service:
        launchctl.change_state(service, enable=False)

    logger.info("%s stopped%s", service.name, " and disabled" if disable_service else "")


def verify_platform() -> None:
    """Verify the platform is supported.

    :raises RuntimeError: When the platform or platform version is not supported.
    """
    logger.debug("Checking platform")

    if platform.system() != "Darwin":
        raise click.ClickException(f"{__package__} requires macOS")

    macos_version = platform.mac_ver()[0]
    macos_version = float(".".join(macos_version.split(".")[:2]))

    if macos_version < MACOS_MIN_VERSION:
        raise click.ClickException(f"{__package__} requires macOS {MACOS_MIN_VERSION} or higher")
