# pylint: disable=missing-function-docstring,missing-module-docstring

import os
import pathlib

import pytest
import pytest_mock

from service import launchctl
from service import Service, locate
from service.service import get_paths


@pytest.mark.parametrize(
    ["domain", "id_", "sudo", "euid"],
    [
        (launchctl.DOMAIN_SYS, f"{launchctl.DOMAIN_SYS}/service", True, 0),
        (f"{launchctl.DOMAIN_GUI}/500", "", False, 500),
    ],
)
def test_service(mocker: pytest_mock.MockerFixture, domain: str, id_: str, sudo: bool, euid: int):
    name = "service"
    sudo_user = "x" if sudo else ""
    path = pathlib.Path(f"/Library/LaunchDaemons/{name}.plist")

    mocker.patch("service.service.os.getenv", return_value=sudo_user)
    mocker.patch("service.service.os.geteuid", return_value=euid)

    service = Service(path)

    assert service.domain == domain
    assert service.file == str(path.absolute())
    assert service.id == id_
    assert service.name == name
    assert str(service.path) == str(path)


@pytest.mark.parametrize(
    ["sudo", "base_path", "message"],
    [
        (False, "/Users/foo", ""),
        (False, "/Library/foo", f"x is not in the {launchctl.DOMAIN_GUI}/{os.geteuid()} domain"),
        (True, "/Library/foo", ""),
        (True, "/System/foo", "x is a macOS system service"),
        (True, "/Users/foo", f"x is not in the {launchctl.DOMAIN_SYS} domain"),
    ],
    ids=["success (gui)", "wrong domain (gui)", "success (sys)", "system service (sys)", "wrong domain (sys)"],
)
def test_validate(mocker: pytest_mock.MockerFixture, sudo: bool, base_path: str, message: str):
    mocker.patch("service.service.os.getenv", return_value="x" if sudo else "")

    service = Service(pathlib.Path(base_path, "x.plist"))

    if message:
        with pytest.raises(RuntimeError, match=message):
            service.validate()
    else:
        assert service.validate() is None


@pytest.mark.parametrize(
    ["name", "exists", "reverse_domains", "full_path"],
    [
        ("xserv.plist", True, True, False),
        ("xserv", True, True, False),
        ("xserv", True, False, False),
        ("xserv", False, True, False),
        ("com.bar.foo.xserv.plist", True, True, False),
        ("/Users/foo/xserv.plist", True, True, True),
    ],
    ids=[
        "name with extension",
        "name without ext",
        "no reverse domains",
        "does not exist",
        "reverse domain in name",
        "full path",
    ],
)
def test_locate(mocker: pytest_mock.MockerFixture, name: str, exists: bool, reverse_domains: bool, full_path: bool):
    mocker.patch("service.service.pathlib.Path.is_file", return_value=exists)

    rds = ["com.bar.foo"] if reverse_domains else []

    if not exists or not reverse_domains:
        match = "No reverse domains configured" if exists else f'Service "{name}" not found'
        with pytest.raises(ValueError, match=match):
            locate(name, rds)
    else:
        result = locate(name, rds)

        if full_path:
            assert result.name == pathlib.Path(name).stem
            assert result.file == str(pathlib.Path(name).absolute())
        else:
            assert result.name == "com.bar.foo.xserv"
            assert result.file == str(pathlib.Path("~/Library/LaunchAgents/com.bar.foo.xserv.plist").expanduser())


@pytest.mark.parametrize(
    ["sudo", "paths"],
    [
        (False, [str(pathlib.Path.home() / "Library/LaunchAgents")]),
        (
            True,
            [
                "/Library/LaunchAgents",
                "/Library/LaunchDaemons",
                "/System/Library/LaunchAgents",
                "/System/Library/LaunchDaemons",
            ],
        ),
        (True, []),
    ],
    ids=["gui domain paths", "sys domain paths", "no paths found"],
)
def test_get_paths(mocker: pytest_mock.MockerFixture, sudo: bool, paths: list[str]):
    mocker.patch("service.service.os.getenv", return_value="x" if sudo else "")

    if not paths:
        mocker.patch("service.service.pathlib.Path.is_dir", return_value=False)

        with pytest.raises(ValueError, match="No service paths found"):
            result = get_paths()
    else:
        result = get_paths()

        assert len(result) == len(paths)
        for path in result:
            assert str(path) in paths
