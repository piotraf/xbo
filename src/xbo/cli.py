"""
xbo - XtraBackup Orchestrator

Configuration (TOML, lowest → highest precedence):

    /etc/xbo/config.toml            system-wide (rpm-friendly)
    ~/.config/xbo/config.toml       per user (XDG)
    --config PATH                   explicit file
    --mysqld / --xtrabackup / --my-cnf   command-line overrides

Example config.toml:

    mysqld = "mysqld"                       # default binary (PATH)

    [xtrabackup]                            # MySQL major -> xtrabackup binary
    "5.7" = "/opt/xtrabackup-2.4/bin/xtrabackup"
    "8.4" = "/opt/xtrabackup-8.4/bin/xtrabackup"

    [instance.prod84]                       # select with: xbo --instance prod84
    mysqld = "/mysqlbin/mysql-8.4.6/bin/mysqld"
    my_cnf = "/db/84/my.cnf"

Usage examples:

    xbo                                     # mysqld from PATH, xtrabackup by MySQL version
    xbo --instance prod84
    xbo --mysqld /mysqlbin/mysql-8.4.6/bin/mysqld --xtrabackup /opt/percona-xtrabackup-8.4/bin/xtrabackup

The versions reported by mysqld --version and xtrabackup --version are checked even when
binary paths are explicitly provided.
"""

import argparse
import datetime
import getpass
import importlib.metadata
import os
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

# per-user file: a fixed /tmp name collides between users (CI runner vs. admin) — sticky /tmp
# lets only the owner replace it.
OUTPUT = Path(tempfile.gettempdir()) / f"xbo_hello_world_{getpass.getuser()}.txt"

SYSTEM_CONFIG = Path("/etc/xbo/config.toml")

# MySQL major -> xtrabackup binary, used when the config does not say otherwise
DEFAULT_XTRABACKUP = {
    "5.6": "/opt/xtrabackup-2.4/bin/xtrabackup",
    "5.7": "/opt/xtrabackup-2.4/bin/xtrabackup",
    "8.0": "/opt/xtrabackup-8.0/bin/xtrabackup",
    "8.4": "/opt/xtrabackup-8.4/bin/xtrabackup",
    "9.7": "/opt/xtrabackup-9.7/bin/xtrabackup",
}


def version() -> str:
    try:
        return importlib.metadata.version("xbo")
    except importlib.metadata.PackageNotFoundError:  # run as a bare script
        return "0+unpackaged"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="xbo", description="XtraBackup Orchestrator")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version()}")
    parser.add_argument("--config", help="Explicit config.toml (on top of /etc and ~/.config)")
    parser.add_argument("--instance", help="Instance name from [instance.<name>] in the config")
    parser.add_argument("--mysqld", help="Path to mysqld binary (default: config, else PATH)")
    parser.add_argument("--xtrabackup", help="Override path to xtrabackup binary")
    parser.add_argument("--my-cnf", dest="my_cnf", help="Path to the instance's my.cnf")
    return parser.parse_args(argv)


def user_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "xbo" / "config.toml"


def _merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, val in src.items():
        if isinstance(val, dict) and isinstance(dst.get(key), dict):
            _merge(dst[key], val)
        else:
            dst[key] = val
    return dst


def load_config(explicit: str | None = None) -> dict[str, Any]:
    """Merge config files lowest → highest precedence. A missing --config is an error;
    missing /etc or ~/.config files are simply skipped."""
    cfg: dict[str, Any] = {}
    for path, required in (
        (SYSTEM_CONFIG, False),
        (user_config_path(), False),
        (Path(explicit) if explicit else None, True),
    ):
        if path is None:
            continue
        if not path.is_file():
            if required:
                raise RuntimeError(f"config not found: {path}")
            continue
        with path.open("rb") as fh:
            _merge(cfg, tomllib.load(fh))
    return cfg


def get_mysql_version(mysqld: str) -> tuple[str, str]:
    result = subprocess.run(
        [mysqld, "--version"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"mysqld --version failed: {mysqld}")

    output = (result.stdout or result.stderr).strip()
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", output)

    if not match:
        raise RuntimeError(f"Cannot determine MySQL version from: {output}")

    db_version = match.group(1)
    db_major = ".".join(db_version.split(".")[:2])

    return db_version, db_major


def get_xtrabackup_binary(db_major: str, mapping: dict[str, str] | None = None) -> Path:
    table = {**DEFAULT_XTRABACKUP, **(mapping or {})}
    try:
        return Path(table[db_major])
    except KeyError:
        raise RuntimeError(f"Unsupported MySQL version: {db_major}") from None


def get_xtrabackup_version(xb_path: Path) -> str:
    if not xb_path.is_file():
        raise RuntimeError(f"xtrabackup binary not found: {xb_path}")

    result = subprocess.run(
        [str(xb_path), "--version"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"xtrabackup --version failed: {xb_path}")

    output = (result.stderr or result.stdout).strip()

    if not output:
        raise RuntimeError(f"Cannot determine xtrabackup version: {xb_path}")

    return output


def main(argv=None) -> int:
    args = parse_args(argv)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cfg = load_config(args.config)

        inst: dict[str, Any] = {}
        if args.instance:
            inst = cfg.get("instance", {}).get(args.instance) or {}
            if not inst:
                raise RuntimeError(f"unknown instance: {args.instance}")

        mysqld = args.mysqld or inst.get("mysqld") or cfg.get("mysqld") or "mysqld"
        my_cnf = args.my_cnf or inst.get("my_cnf")

        db_version, db_major = get_mysql_version(mysqld)

        xb_override = args.xtrabackup or inst.get("xtrabackup")
        if xb_override:
            xb_path = Path(xb_override)
        else:
            xb_path = get_xtrabackup_binary(db_major, cfg.get("xtrabackup"))

        xb_version = get_xtrabackup_version(xb_path)

    except (FileNotFoundError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        OUTPUT.write_text(f"hello world from xbo: {now}\nERROR: {exc}\n")
        return 1

    OUTPUT.write_text(
        f"hello world from xbo: {now}\n"
        f"instance: {args.instance or '-'}\n"
        f"mysql: {db_version}\n"
        f"mysqld: {mysqld}\n"
        f"my.cnf: {my_cnf or '-'}\n"
        f"xtrabackup: {xb_path}\n"
        f"xtrabackup version: {xb_version}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
