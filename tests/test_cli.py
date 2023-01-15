# pylint: disable=missing-function-docstring,missing-module-docstring

import pathlib
import subprocess
import typing as t

import click
from click.testing import CliRunner
import pytest
import pytest_mock

import service.cli


@pytest.mark.parametrize(
    ["data", "rev_domains", "output"],
    [
        ({"reverse-domains": ["com.foo.bar"]}, ["com.foo.bar"], ""),
        (None, [], ""),
        ({}, [], ""),
        ({"reverse-domains": {}}, [], 'Warning: Invalid configuration file. "reverse-domains" must be a list.\n'),
    ],
    ids=["config ok", "no data", "config key missing", "config invalid"],
)
def test_get_reverse_domains(
    capsys: pytest.CaptureFixture, data: t.Optional[dict[str, list[str]]], rev_domains: list[str], output: str
):
    result = service.cli.get_reverse_domains(data)
    captured = capsys.readouterr()

    assert result == rev_domains
    assert captured.err == output


@pytest.mark.parametrize(
    ["name", "version", "message"],
    [
        ("Darwin", str(service.cli.MACOS_MIN_VERSION), None),
        ("x", str(service.cli.MACOS_MIN_VERSION), "requires"),
        ("Darwin", str(service.cli.MACOS_MIN_VERSION - 1), str(service.cli.MACOS_MIN_VERSION)),
    ],
    ids=["supported", "unsupported (system)", "unsupported (version)"],
)
def test_verify_platform(mocker: pytest_mock.MockerFixture, name: str, version: str, message: str):
    mocker.patch("service.cli.platform.system", return_value=name)
    mocker.patch("service.cli.platform.mac_ver", return_value=[version])

    if message:
        with pytest.raises(click.ClickException) as exc:
            service.cli.verify_platform()

        assert message in str(exc)
    else:
        assert service.cli.verify_platform() is None


@pytest.fixture(name="config_file")
def fixture_config_file(tmp_path: pathlib.Path):
    data = 'reverse-domains = ["com.bar.foo"]\n'
    file = tmp_path / "config.toml"
    file.write_text(data)
    return file


@pytest.mark.parametrize(["error"], [(False,), (True,)], ids=["success", "fail"])
def test_cli_disable(mocker: pytest_mock.MockerFixture, config_file: pathlib.Path, error: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")
    mocker.patch(
        "service.launchctl.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
        side_effect=subprocess.CalledProcessError(1, []) if error else None,
    )
    mocker.patch("service.service.pathlib.Path.is_file", return_value=True)

    runner = CliRunner()
    result = runner.invoke(service.cli.cli, ["--config", str(config_file), "disable", "srvc"])

    if error:
        assert result.exit_code == 1
        assert result.output == "Error: Failed to disable com.bar.foo.srvc\n"
    else:
        assert result.exit_code == 0
        assert result.output == "com.bar.foo.srvc disabled\n"


@pytest.mark.parametrize(["error"], [(False,), (True,)], ids=["success", "fail"])
def test_cli_enable(mocker: pytest_mock.MockerFixture, config_file: pathlib.Path, error: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")
    mocker.patch(
        "service.launchctl.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
        side_effect=subprocess.CalledProcessError(1, []) if error else None,
    )
    mocker.patch("service.service.pathlib.Path.is_file", return_value=True)

    runner = CliRunner()
    result = runner.invoke(service.cli.cli, ["--config", str(config_file), "enable", "srvc"])

    if error:
        assert result.exit_code == 1
        assert result.output == "Error: Failed to enable com.bar.foo.srvc\n"
    else:
        assert result.exit_code == 0
        assert result.output == "com.bar.foo.srvc enabled\n"


@pytest.mark.parametrize(["error"], [(False,), (True,)], ids=["success", "fail"])
def test_cli_restart(mocker: pytest_mock.MockerFixture, config_file: pathlib.Path, error: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")
    mocker.patch(
        "service.launchctl.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
        side_effect=subprocess.CalledProcessError(1, []) if error else None,
    )
    mocker.patch("service.service.pathlib.Path.is_file", return_value=True)

    runner = CliRunner()
    result = runner.invoke(service.cli.cli, ["--config", str(config_file), "restart", "srvc"])

    if error:
        assert result.exit_code == 1
        assert result.output == "Error: Failed to stop com.bar.foo.srvc\n"
    else:
        assert result.exit_code == 0
        assert result.output == "com.bar.foo.srvc restarted\n"


@pytest.mark.parametrize(
    ["enable", "error"], [(False, False), (True, False), (False, True)], ids=["success", "success (enable)", "fail"]
)
def test_cli_start(mocker: pytest_mock.MockerFixture, config_file: pathlib.Path, enable: bool, error: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")
    mocker.patch(
        "service.launchctl.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
        side_effect=subprocess.CalledProcessError(1, []) if error else None,
    )
    mocker.patch("service.service.pathlib.Path.is_file", return_value=True)

    subcmd = ["start"]
    if enable:
        subcmd.append("--enable")

    runner = CliRunner()
    result = runner.invoke(service.cli.cli, ["--config", str(config_file), *subcmd, "srvc"])

    if error:
        assert result.exit_code == 1
        assert result.output == "Error: Failed to start com.bar.foo.srvc\n"
    else:
        assert result.exit_code == 0
        assert result.output == f'com.bar.foo.srvc {"enabled and " if enable else ""}started\n'


@pytest.mark.parametrize(
    ["disable", "error"], [(False, False), (True, False), (False, True)], ids=["success", "success (disable)", "fail"]
)
def test_cli_stop(mocker: pytest_mock.MockerFixture, config_file: pathlib.Path, disable: bool, error: bool):
    mocker.patch("service.cli.os.getenv", return_value="x")
    mocker.patch(
        "service.launchctl.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0),
        side_effect=subprocess.CalledProcessError(1, []) if error else None,
    )
    mocker.patch("service.service.pathlib.Path.is_file", return_value=True)

    subcmd = ["stop"]
    if disable:
        subcmd.append("--disable")

    runner = CliRunner()
    result = runner.invoke(service.cli.cli, ["--config", str(config_file), *subcmd, "srvc"])

    if error:
        assert result.exit_code == 1
        assert result.output == "Error: Failed to stop com.bar.foo.srvc\n"
    else:
        assert result.exit_code == 0
        assert result.output == f'com.bar.foo.srvc stopped{" and disabled" if disable else ""}\n'
