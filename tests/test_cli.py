import stat
from pathlib import Path

import pytest

from xbo import cli


def fake_bin(tmp_path: Path, name: str, output: str) -> Path:
    p = tmp_path / name
    p.write_text(f'#!/bin/sh\necho "{output}"\n')
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_version_string():
    assert cli.version()


def test_get_mysql_version_parses(tmp_path):
    mysqld = fake_bin(tmp_path, "mysqld", "/usr/sbin/mysqld  Ver 8.4.11 for Linux on x86_64")
    assert cli.get_mysql_version(str(mysqld)) == ("8.4.11", "8.4")


def test_get_mysql_version_rejects_garbage(tmp_path):
    mysqld = fake_bin(tmp_path, "mysqld", "no version here")
    with pytest.raises(RuntimeError):
        cli.get_mysql_version(str(mysqld))


@pytest.mark.parametrize(
    ("major", "expected"),
    [("5.7", "/opt/xtrabackup-2.4/bin/xtrabackup"), ("8.4", "/opt/xtrabackup-8.4/bin/xtrabackup")],
)
def test_xtrabackup_mapping(major, expected):
    assert str(cli.get_xtrabackup_binary(major)) == expected


def test_unsupported_major():
    with pytest.raises(RuntimeError):
        cli.get_xtrabackup_binary("4.1")


def test_main_with_overrides(tmp_path, monkeypatch):
    mysqld = fake_bin(tmp_path, "mysqld", "mysqld  Ver 8.4.11")
    xb = fake_bin(tmp_path, "xtrabackup", "xtrabackup version 8.4.0-7")
    out = tmp_path / "out.txt"
    monkeypatch.setattr(cli, "OUTPUT", out)
    assert cli.main(["--mysqld", str(mysqld), "--xtrabackup", str(xb)]) == 0
    text = out.read_text()
    assert "mysql: 8.4.11" in text and f"xtrabackup: {xb}" in text


def test_main_missing_xtrabackup_returns_1(tmp_path, monkeypatch):
    mysqld = fake_bin(tmp_path, "mysqld", "mysqld  Ver 8.4.11")
    out = tmp_path / "out.txt"
    monkeypatch.setattr(cli, "OUTPUT", out)
    assert cli.main(["--mysqld", str(mysqld), "--xtrabackup", str(tmp_path / "nope")]) == 1
    assert "ERROR:" in out.read_text()
