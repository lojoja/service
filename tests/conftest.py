# pylint: disable=missing-module-docstring,missing-function-docstring

from pathlib import Path

import pytest


@pytest.fixture(name="config", scope="session")
def config_fixture(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A config file with reverse domains for tests."""
    data = 'reverse-domains = ["com.bar.foo"]\n'
    file = tmp_path_factory.getbasetemp() / "config.toml"
    file.write_text(data, encoding="utf8")
    return file


@pytest.fixture(name="plist", scope="session")
def plist_fixture(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Creates a (blank) service plist file for tests that require it to exist."""
    file = tmp_path_factory.getbasetemp() / "xserv.plist"
    file.touch(exist_ok=True)
    return file
