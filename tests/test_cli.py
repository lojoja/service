# pylint: disable=missing-module-docstring,missing-function-docstring,too-many-arguments,too-many-positional-arguments

from contextlib import nullcontext as does_not_raise
from pathlib import Path
import subprocess
import typing as t

import click
from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture

from service.cli import cli, get_service, get_reverse_domains, verify_platform, MACOS_MIN_VERSION
from service.service import Service


@pytest.mark.parametrize("data", [None, {}, {"reverse-domains": ["com.foo.bar"]}, {"reverse-domains": {}}])
def test_get_reverse_domains(capsys: pytest.CaptureFixture, data: t.Optional[dict[str, list[str]]]):
    reverse_domains = data.get("reverse-domains", []) if isinstance(data, dict) else []
    output = ""

    if not isinstance(reverse_domains, list):
        reverse_domains = []
        output = 'Warning: Invalid configuration file. "reverse-domains" must be a list.\n'

    result = get_reverse_domains(data)

    assert result == reverse_domains
    assert capsys.readouterr().err == output


def test_get_service(mocker: MockerFixture):
    mocker.patch("service.cli.Path.is_file", return_value=True)
    ctx = click.Context(click.Command("cmd"))
    ctx.obj = ["com.foo.bar"]

    get_service(ctx, click.Option(["-x"]), "name")

    assert isinstance(ctx.obj, Service)
    assert ctx.obj.path == Path("~/Library/LaunchAgents/com.foo.bar.name.plist").expanduser().absolute()


@pytest.mark.parametrize("version_offset", [-1, 0, 1])
@pytest.mark.parametrize("name", ["Darwin", "x"])
def test_verify_platform(mocker: MockerFixture, name: str, version_offset: int):
    mocker.patch("service.cli.platform.system", return_value=name)
    mocker.patch("service.cli.platform.mac_ver", return_value=[str(MACOS_MIN_VERSION + version_offset)])
    context = does_not_raise()

    if name != "Darwin":
        context = pytest.raises(click.ClickException, match=r".* requires macOS$")
    elif version_offset < 0:
        context = pytest.raises(click.ClickException, match=rf".* requires macOS {MACOS_MIN_VERSION} or higher")

    with context:
        verify_platform()


def test_cli_version(config: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "--version"])
    assert result.output.startswith("cli, version")


@pytest.mark.parametrize("short_opts", [True, False])
@pytest.mark.parametrize("verbose", [True, False])
def test_cli_verbosity(caplog: pytest.LogCaptureFixture, config: Path, verbose: bool, short_opts: bool):
    CliRunner().invoke(
        cli, ["-c", str(config), "start", "--help", ("-v" if short_opts else "--verbose") if verbose else ""]
    )
    assert ("DEBUG" in caplog.text) is verbose


def test_cli_verifies_platform(mocker: MockerFixture, config: Path):
    mock_verify_platform = mocker.patch("service.cli.verify_platform")
    CliRunner().invoke(cli, ["-c", str(config), "start", "--help"])  # arbitrary no-op command
    mock_verify_platform.assert_called_once()


@pytest.mark.parametrize("should_fail", [True, False])
def test_cli_disable(mocker: MockerFixture, config: Path, plist: Path, should_fail: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")  # use system domain
    mock_run = mocker.patch("service.cli.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    output = f"{plist.stem} disabled\n"

    if should_fail:
        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        output = f"Error: Failed to disable {plist.stem}\n"

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "disable", str(plist.absolute())])

    assert result.exit_code == int(should_fail)
    assert result.output == output


@pytest.mark.parametrize("should_fail", [True, False])
def test_cli_enable(mocker: MockerFixture, config: Path, plist: Path, should_fail: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")  # use system domain
    mock_run = mocker.patch("service.cli.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    output = f"{plist.stem} enabled\n"

    if should_fail:
        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        output = f"Error: Failed to enable {plist.stem}\n"

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "enable", str(plist.absolute())])

    assert result.exit_code == int(should_fail)
    assert result.output == output


@pytest.mark.parametrize("should_fail", [True, False])
def test_cli_restart(mocker: MockerFixture, config: Path, plist: Path, should_fail: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")  # use system domain
    mock_run = mocker.patch("service.cli.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    output = f"{plist.stem} restarted\n"

    if should_fail:
        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        output = f"Error: Failed to stop {plist.stem}\n"

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "restart", str(plist.absolute())])

    assert result.exit_code == int(should_fail)
    assert result.output == output


@pytest.mark.parametrize("short_opts", [True, False])
@pytest.mark.parametrize("enable", [True, False])
@pytest.mark.parametrize("should_fail", [True, False])
def test_cli_start(mocker: MockerFixture, config: Path, plist: Path, should_fail: bool, enable: bool, short_opts: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")  # use system domain
    mock_run = mocker.patch("service.cli.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    output = f"{plist.stem} {'enabled and ' if enable else ''}started\n"

    if should_fail:
        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        output = f"Error: Failed to {'enable' if enable else 'start'} {plist.stem}\n"

    args = ["-c", str(config), "start"]

    if enable:
        args.append("-e" if short_opts else "--enable")

    args.append(str(plist.absolute()))

    runner = CliRunner()
    result = runner.invoke(cli, args)

    assert result.exit_code == int(should_fail)
    assert result.output == output


@pytest.mark.parametrize("short_opts", [True, False])
@pytest.mark.parametrize("disable", [True, False])
@pytest.mark.parametrize("should_fail", [True, False])
def test_cli_stop(mocker: MockerFixture, config: Path, plist: Path, should_fail: bool, disable: bool, short_opts: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")  # use system domain
    mock_run = mocker.patch("service.cli.launchctl.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    output = f"{plist.stem} stopped{' and disabled' if disable else ''}\n"

    if should_fail:
        mock_run.side_effect = subprocess.CalledProcessError(1, [])
        output = f"Error: Failed to stop {plist.stem}\n"

    args = ["-c", str(config), "stop"]

    if disable:
        args.append("-d" if short_opts else "--disable")

    args.append(str(plist.absolute()))

    runner = CliRunner()
    result = runner.invoke(cli, args)

    assert result.exit_code == int(should_fail)
    assert result.output == output
