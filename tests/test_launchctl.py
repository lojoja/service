# pylint: disable=missing-function-docstring,missing-module-docstring

import pathlib
import subprocess

import pytest
import pytest_mock

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
        (True, 0, ""),
        (False, 0, ""),
        (True, launchctl.ERROR_GUI_ALREADY_STARTED, "x is already started"),
        (True, launchctl.ERROR_SYS_ALREADY_STARTED, "x is already started"),
        (True, 10000, "Failed to start x"),
        (True, launchctl.ERROR_SIP, "Failed to start x due to SIP"),
        (False, launchctl.ERROR_GUI_ALREADY_STOPPED, "x is already stopped"),
        (False, launchctl.ERROR_SYS_ALREADY_STOPPED, "x is already stopped"),
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
def test_boot(mocker: pytest_mock.MockerFixture, run: bool, returncode: int, message: str):
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
    ["sudo", "enable", "message"],
    [
        (False, True, "Cannot change service state"),
        (True, True, ""),
        (True, True, "Failed to enable x"),
        (True, False, ""),
        (True, False, "Failed to disable x"),
    ],
    ids=["non-system domain", "enable (success)", "enable (fail)", "disable (success)", "disable (fail)"],
)
def test_change_state(mocker: pytest_mock.MockerFixture, sudo: bool, enable: bool, message: str):
    mocker.patch("service.service.os.getenv", return_value="x" if sudo else "")

    service = Service(pathlib.Path("x"))

    if message:
        mocker.patch("service.launchctl.subprocess.run", side_effect=subprocess.CalledProcessError(1, []))

        with pytest.raises(RuntimeError) as exc:
            launchctl.change_state(service, enable)

        assert message in str(exc)
    else:
        mocker.patch("service.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))

        assert launchctl.boot(service, enable) is None
