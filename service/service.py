"""
service.service

MacOS System and GUI domain services.
"""

import logging
import os
from pathlib import Path

from . import launchctl


__all__ = ["locate", "Service"]


logger = logging.getLogger(__name__)


class Service:
    """A LaunchAgent or LaunchDaemon service."""

    def __init__(self, path: Path):
        self._path = path

    @property
    def domain(self) -> str:
        """The service domain."""
        return launchctl.DOMAIN_SYS if os.getenv("SUDO_USER") else f"{launchctl.DOMAIN_GUI}/{os.geteuid()}"

    @property
    def file(self) -> str:
        """The absolute path to the service file."""
        return str(self._path.absolute())

    @property
    def id(self) -> str:  # pylint: disable=c0103
        """The service ID in the system domain."""
        return "/".join([self.domain, self.name]) if os.getenv("SUDO_USER") else ""

    @property
    def name(self) -> str:
        """The service name (service file name without extension)."""
        return self._path.stem

    @property
    def path(self) -> Path:
        """The path to the service file."""
        return self._path

    def validate(self) -> None:
        """Validate the service.

        A service is considered valid if it is part of the active domain and is not a macOS system service.

        Raises:
            RuntimeError: When the service is not valid.
        """
        if self.domain == launchctl.DOMAIN_SYS:
            if self.file.startswith("/System"):
                raise RuntimeError(f"{self.name} is a macOS system service")

            if self.file.startswith("/Users"):
                raise RuntimeError(f"{self.name} is not in the {self.domain} domain")
        else:
            if not self.file.startswith("/Users"):
                raise RuntimeError(f"{self.name} is not in the {self.domain} domain")


def locate(name: str, reverse_domains: list[str]) -> Service:
    """
    Locate a service.

    If an absolute or relative path is part of `name` that path is used to find the service. If a path is not present
    all directories containing services for the current domain will be searched.

    Args:
        name: The service name, with optional absolute/relative path and file extension.
        reverse_domains: A list of reverse domains to prepend to the service name.

    Raises:
        ValueError: When a service is not found or a service name without path and/or domain is provided and there no
                    reverse domains are configured.
    """
    logger.debug('Locating service "%s"', name)
    original_name = name
    service_path = None

    if not name.endswith(".plist"):
        name = f"{name}.plist"

    path = Path(name)

    logger.debug("Generating potential file paths")

    if len(path.parts) > 1:
        file_paths = [path.expanduser().absolute()]
    else:
        if len(path.suffixes) > 1:
            file_names = [path.name]
        else:
            if reverse_domains:
                file_names = [f"{rd}.{path.name}" for rd in reverse_domains]
            else:
                raise ValueError("No reverse domains configured")

        file_paths = [p.joinpath(n) for p in get_paths() for n in file_names]

    for file_path in file_paths:
        logger.debug('Trying "%s"', file_path)

        if file_path.is_file():
            service_path = file_path
            break

    if not service_path:
        raise ValueError(f'Service "{original_name}" not found')

    logger.debug('Service found, using "%s"', service_path)
    service = Service(service_path)

    logger.debug("Validating service")
    service.validate()

    return service


def get_paths() -> list[Path]:
    """Get service paths for the active domain.

    Raises:
        ValueError: When no service paths are found.
    """
    logger.debug("Identifying service paths")

    base_paths = ["/", "/System"] if os.getenv("SUDO_USER") else [Path.home()]
    service_paths = []

    for base in base_paths:
        for path in ["Library/LaunchAgents", "Library/LaunchDaemons"]:
            service_path = Path(base, path)

            if service_path.is_dir():
                service_paths.append(service_path)

    if not service_paths:
        raise ValueError("No service paths found")

    return service_paths
