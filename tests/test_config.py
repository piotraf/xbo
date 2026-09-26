from pathlib import Path

import pytest

from xbo import cli


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """No /etc file, ~/.config under tmp_path."""
    monkeypatch.setattr(cli, "SYSTEM_CONFIG", tmp_path / "etc" / "config.toml")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return tmp_path


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_no_files_gives_empty_config(isolated_config):
    assert cli.load_config() == {}


def test_precedence_system_user_explicit(isolated_config):
    write(
        isolated_config / "etc" / "config.toml", 'mysqld = "sys"\n[xtrabackup]\n"8.4" = "/sys/xb"\n'
    )
    write(isolated_config / "xdg" / "xbo" / "config.toml", 'mysqld = "user"\n')
    explicit = write(isolated_config / "explicit.toml", '[xtrabackup]\n"8.4" = "/explicit/xb"\n')
    cfg = cli.load_config(str(explicit))
    assert cfg["mysqld"] == "user"  # user beats system
    assert cfg["xtrabackup"]["8.4"] == "/explicit/xb"  # explicit beats both; tables merge


def test_missing_explicit_config_is_an_error(isolated_config):
    with pytest.raises(RuntimeError, match="config not found"):
        cli.load_config(str(isolated_config / "nope.toml"))


def test_xtrabackup_mapping_from_config_overrides_default():
    assert str(cli.get_xtrabackup_binary("8.4", {"8.4": "/custom/xb"})) == "/custom/xb"
    assert (
        str(cli.get_xtrabackup_binary("5.7", {"8.4": "/custom/xb"}))
        == cli.DEFAULT_XTRABACKUP["5.7"]
    )


def test_unknown_instance_returns_1(isolated_config, monkeypatch):
    out = isolated_config / "out.txt"
    monkeypatch.setattr(cli, "OUTPUT", out)
    assert cli.main(["--instance", "ghost"]) == 1
    assert "unknown instance: ghost" in out.read_text()
