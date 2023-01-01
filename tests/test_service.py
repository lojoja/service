# pylint: disable=c0114,c0116,r0913

import pathlib

import pytest
from pytest_mock.plugin import MockerFixture

from service import launchctl
from service import Service, locate
from service.service import get_paths


@pytest.mark.parametrize(
    ["name", "domain", "id_", "sudo_user", "euid"],
    [
        ("service", launchctl.DOMAIN_SYS, f"{launchctl.DOMAIN_SYS}/service", "x", 0),
        ("service", f"{launchctl.DOMAIN_GUI}/500", "", None, 500),
    ],
)
def test_service(mocker: MockerFixture, name: str, domain: str, id_: str, sudo_user: str | None, euid: int):
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
    ["sudo_user", "base_path", "message"],
    [
        (None, "/Users/foo", None),
        (None, "/Library/foo", "domain"),
        ("x", "/Library/foo", None),
        ("x", "/System/foo", "macOS"),
        ("x", "/Users/foo", "domain"),
    ],
    ids=["success (gui)", "wrong domain (gui)", "success (sys)", "system service (sys)", "wrong domain (sys)"],
)
def test_validate(mocker: MockerFixture, sudo_user: str | None, base_path: str, message: str | None):
    mocker.patch("service.service.os.getenv", return_value=sudo_user)

    service = Service(pathlib.Path(base_path, "x.plist"))

    if message:
        with pytest.raises(RuntimeError) as exc:
            service.validate()

        assert message in str(exc)
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
def test_locate(mocker: MockerFixture, name: str, exists: bool, reverse_domains: bool, full_path: bool):
    mocker.patch("service.service.pathlib.Path.is_file", return_value=exists)

    rds = ["com.bar.foo"] if reverse_domains else []

    if not exists or not reverse_domains:
        with pytest.raises(ValueError) as exc:
            locate(name, rds)

        if not exists:
            assert "not found" in str(exc)
        else:
            assert "configured" in str(exc)
    else:
        result = locate(name, rds)

        assert result.name == pathlib.Path(name).stem if full_path else "com.bar.foo.xserv"
        assert (
            result.file == str(pathlib.Path(name).absolute())
            if full_path
            else str(pathlib.Path("~/Library/LaunchAgents/com.bar.foo.xserv").expanduser())
        )


@pytest.mark.parametrize(
    ["sudo_user", "paths"],
    [
        (None, [str(pathlib.Path.home() / "Library/LaunchAgents")]),
        (
            "x",
            [
                "/Library/LaunchAgents",
                "/Library/LaunchDaemons",
                "/System/Library/LaunchAgents",
                "/System/Library/LaunchDaemons",
            ],
        ),
        ("x", []),
    ],
    ids=["gui domain paths", "sys domain paths", "no paths found"],
)
def test_get_paths(mocker: MockerFixture, sudo_user: str | None, paths: list[str]):
    mocker.patch("service.service.os.getenv", return_value=sudo_user)

    if not paths:
        mocker.patch("service.service.pathlib.Path.is_dir", return_value=False)

        with pytest.raises(ValueError) as exc:
            result = get_paths()

        assert "found" in str(exc)
    else:
        result = get_paths()

        assert len(result) == len(paths)
        for path in result:
            assert str(path) in paths
