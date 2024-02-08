# pylint: disable=missing-module-docstring,missing-function-docstring,protected-access

from contextlib import nullcontext as does_not_raise
from pathlib import Path
import subprocess

import pytest
from pytest_mock import MockerFixture

from service.launchctl import (
    _execute,
    boot,
    change_state,
    DOMAIN_GUI,
    DOMAIN_SYS,
    ERROR_GUI_ALREADY_STARTED,
    ERROR_GUI_ALREADY_STOPPED,
    ERROR_SIP,
    ERROR_SYS_ALREADY_STARTED,
    ERROR_SYS_ALREADY_STOPPED,
)
from service.service import Service


def test__execute(mocker: MockerFixture):
    subcommand = "bootstrap"
    subcommand_args = [DOMAIN_GUI, "/foo"]
    subprocess_mock = mocker.patch("service.launchctl.subprocess.run")

    _execute(subcommand, *subcommand_args)

    subprocess_mock.assert_called_once_with(
        ["launchctl", subcommand, *subcommand_args], check=True, capture_output=True
    )


@pytest.mark.parametrize(
    "return_code",
    [
        0,
        ERROR_GUI_ALREADY_STARTED,
        ERROR_GUI_ALREADY_STOPPED,
        ERROR_SIP,
        ERROR_SYS_ALREADY_STARTED,
        ERROR_SYS_ALREADY_STOPPED,
    ],
)
@pytest.mark.parametrize("run", [True, False])
def test_boot(mocker: MockerFixture, run: bool, return_code: int):
    mock_run = mocker.patch("service.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    context = does_not_raise()
    service = Service(Path("xserv.plist"))

    if return_code != 0:
        if return_code in [10000, ERROR_SIP]:
            msg = f"Failed to {'start' if run else 'stop'} {service.name}"
            msg += " due to SIP" if return_code == ERROR_SIP else ""
        else:
            msg = f"{service.name} is already {'started' if run else 'stopped'}"

        mock_run.side_effect = subprocess.CalledProcessError(return_code, [])
        context = pytest.raises(RuntimeError, match=msg)

    with context:
        boot(service, run=run)

    mock_run.assert_called_once_with(
        ["launchctl", "bootstrap" if run else "bootout", service.domain, service.file], check=True, capture_output=True
    )


@pytest.mark.parametrize("should_fail", [True, False])
@pytest.mark.parametrize("subcmd", ["enable", "disable"])
@pytest.mark.parametrize("domain", [DOMAIN_SYS, DOMAIN_GUI])
def test_change_state(mocker: MockerFixture, domain: str, subcmd: str, should_fail: bool):
    mocker.patch("service.service.os.getenv", return_value="x" if domain == DOMAIN_SYS else "")
    mock_run = mocker.patch("service.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    context = does_not_raise()
    service = Service(Path("xserv.plist"))

    if should_fail or domain == DOMAIN_GUI:  # The gui domain should always fail regardless of the test param
        if domain == DOMAIN_GUI:
            msg = f'Cannot change service state in the "{service.domain}" domain'
        else:
            msg = f"Failed to {subcmd} {service.name}"

        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        context = pytest.raises(RuntimeError, match=msg)

    with context:
        change_state(service, enable=subcmd == "enable")

    if domain == DOMAIN_GUI:
        mock_run.assert_not_called()
    else:
        mock_run.assert_called_once_with(["launchctl", subcmd, service.id], check=True, capture_output=True)
