# pylint: disable=missing-module-docstring,missing-function-docstring

from contextlib import nullcontext as does_not_raise
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from service.launchctl import DOMAIN_GUI, DOMAIN_SYS
from service.service import Service, get_paths, locate


@pytest.mark.parametrize("domain", [DOMAIN_SYS, DOMAIN_GUI])
def test_service(mocker: MockerFixture, domain: str):
    mocker.patch("service.service.os.getenv", return_value="x" if domain == DOMAIN_SYS else "")
    mocker.patch("service.service.os.geteuid", return_value=0 if domain == DOMAIN_SYS else 500)
    path = Path("xserv.plist")
    service = Service(path)

    assert service.domain == f"{domain}{'/500' if domain == DOMAIN_GUI else ''}"
    assert service.file == str(path.absolute())
    assert service.id == (f"{DOMAIN_SYS}/{path.stem}" if domain == DOMAIN_SYS else "")
    assert service.name == path.stem
    assert service.path == path


@pytest.mark.parametrize(
    "base_path", ["/Library/LaunchAgents", "/System/Library/LaunchAgents", "/Users/foo/Library/LaunchAgents"]
)
@pytest.mark.parametrize("domain", [DOMAIN_SYS, DOMAIN_GUI])
def test_service_validate(mocker: MockerFixture, domain: str, base_path: str):
    mocker.patch("service.service.os.getenv", return_value="x" if domain == DOMAIN_SYS else "")
    mocker.patch("service.service.os.geteuid", return_value=0 if domain == DOMAIN_SYS else 500)
    service = Service(Path(base_path, "xserv.plist"))
    context = does_not_raise()

    if domain == DOMAIN_SYS and base_path.startswith("/System"):
        context = pytest.raises(RuntimeError, match=f"{service.name} is a macOS system service")
    elif domain == DOMAIN_SYS and base_path.startswith("/Users"):
        context = pytest.raises(RuntimeError, match=f"{service.name} is not in the {DOMAIN_SYS} domain")
    elif domain == DOMAIN_GUI and not base_path.startswith("/Users"):
        context = pytest.raises(RuntimeError, match=f"{service.name} is not in the {DOMAIN_GUI}/500 domain")

    with context:
        service.validate()


@pytest.mark.parametrize(
    "name",
    [
        "xserv",
        "xserv.plist",
        "org.foo.xserv",
        "org.foo.xserv.plist",
        "dir/xserv",
        "dir/xserv.plist",
        "dir/org.foo.xserv",
        "dir/org.foo.xserv.plist",
        "/Users/foo/xserv",
        "/Users/foo/xserv.plist",
        "/Users/foo/org.foo.xserv",
        "/Users/foo/org.foo.xserv.plist",
    ],
)
@pytest.mark.parametrize("reverse_domains", [[], ["com.foo.bar"]])
@pytest.mark.parametrize("exists", [True, False])
def test_locate(mocker: MockerFixture, exists: bool, reverse_domains: list[str], name: str):
    mocker.patch("service.service.os.getenv", return_value="")
    mocker.patch("service.service.pathlib.Path.is_file", return_value=exists)
    name_has_path = len(name.split("/")) > 1
    name_has_reverse_domain = len(name.split(".")) > 2

    context = does_not_raise()

    if not reverse_domains and not name_has_path and not name_has_reverse_domain:
        context = pytest.raises(ValueError, match="No reverse domains configured")
    elif not exists:
        context = pytest.raises(ValueError, match=f'Service "{name}" not found')

    with context:
        result = locate(name, reverse_domains)

    if isinstance(context, does_not_raise):
        resolved_name = "".join(
            [
                "" if name_has_path else "~/Library/LaunchAgents/",
                "" if name_has_path or name_has_reverse_domain else f"{reverse_domains[0]}.",
                name,
                "" if name.endswith(".plist") else ".plist",
            ]
        )

        assert result.path == Path(resolved_name).expanduser().absolute()


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("domain", [DOMAIN_SYS, DOMAIN_GUI])
def test_get_paths(mocker: MockerFixture, domain: str, exists: bool):
    mocker.patch("service.service.os.getenv", return_value="x" if domain == DOMAIN_SYS else "")
    mocker.patch("service.service.pathlib.Path.is_dir", return_value=exists)
    paths = [
        Path(base, path)
        for base in (["/", "/System"] if domain == DOMAIN_SYS else [Path.home()])
        for path in ["Library/LaunchAgents", "Library/LaunchDaemons"]
    ]
    context = does_not_raise() if exists else pytest.raises(ValueError, match="No service paths found")

    with context:
        result = get_paths()

    if exists:
        assert len(result) == len(paths)
        assert all(path in result for path in paths)
