# pylint: disable=c0114,c0116,r0913

import pathlib
import subprocess

import pytest
from pytest_mock.plugin import MockerFixture

from service import launchctl
from service import Service


def test__execute_command(tmp_path: pathlib.Path):
    path = str(tmp_path / "x.plist")

    # The call fails intentionally so the constructed command can be tested.
    try:
        launchctl._execute("bootstrap", launchctl.DOMAIN_GUI, str(path))  # pylint: disable=w0212
    except subprocess.CalledProcessError as exc:
        assert exc.cmd == ["launchctl", "bootstrap", launchctl.DOMAIN_GUI, str(path)]
        assert exc.returncode > 0


@pytest.mark.parametrize(
    ["run", "returncode", "message"],
    [
        (True, 0, None),
        (False, 0, None),
        (True, launchctl.ERROR_GUI_ALREADY_STARTED, "started"),
        (True, launchctl.ERROR_SYS_ALREADY_STARTED, "started"),
        (True, 10000, "Failed"),
        (True, launchctl.ERROR_SIP, "due to SIP"),
        (False, launchctl.ERROR_GUI_ALREADY_STOPPED, "stopped"),
        (False, launchctl.ERROR_SYS_ALREADY_STOPPED, "stopped"),
    ],
    ids=[
        "success (start)",
        "success (stop)",
        "start already running (gui)",
        "start already running (sys)",
        "failed",
        "failed (SIP)",
        "stop already stopped (gui)",
        "stop already stopped (sys)",
    ],
)
def test_boot(
    mocker: MockerFixture,
    run: bool,
    returncode: int,
    message: str | None,
):
    service = Service(pathlib.Path("x"))

    if message:
        mocker.patch("service.launchctl.subprocess.run", side_effect=subprocess.CalledProcessError(returncode, []))

        with pytest.raises(RuntimeError) as exc:
            launchctl.boot(service, run)

        assert message in str(exc)
    else:
        mocker.patch("service.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], returncode))

        assert launchctl.boot(service, run) is None


@pytest.mark.parametrize(
    ["sudo_user", "enable", "message"],
    [(None, True, "domain"), ("x", True, None), ("x", False, None), ("x", True, "Failed")],
    ids=["non-system domain", "success (enable)", "success (disable)", "failed"],
)
def test_change_state(mocker: MockerFixture, sudo_user: str | None, enable: bool, message: str):
    mocker.patch("service.service.os.getenv", return_value=sudo_user)

    service = Service(pathlib.Path("x"))

    if message:
        mocker.patch("service.launchctl.subprocess.run", side_effect=subprocess.CalledProcessError(1, []))

        with pytest.raises(RuntimeError) as exc:
            launchctl.change_state(service, enable)

        assert message in str(exc)
    else:
        mocker.patch("service.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))

        assert launchctl.boot(service, enable) is None
