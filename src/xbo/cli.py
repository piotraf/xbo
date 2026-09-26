"""
xbo - XtraBackup Orchestrator

Usage examples:

    # Use mysqld from PATH and automatically select the required XtraBackup:
    xbo

    # Override the mysqld and XtraBackup binary paths:
    xbo --mysqld /mysqlbin/mysql-8.4.6/bin/mysqld \
        --xtrabackup /opt/percona-xtrabackup-8.4/bin/xtrabackup

The versions reported by both mysqld --version and xtrabackup --version
are checked even when binary paths are explicitly provided.
"""

import argparse
import datetime
import importlib.metadata
import re
import subprocess
from pathlib import Path

OUTPUT = Path("/tmp/xbo_hello_world.txt")


def version() -> str:
    try:
        return importlib.metadata.version("xbo")
    except importlib.metadata.PackageNotFoundError:  # run as a bare script
        return "0+unpackaged"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="xbo", description="XtraBackup Orchestrator")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version()}")
    parser.add_argument(
        "--mysqld",
        default="mysqld",
        help="Path to mysqld binary (default: mysqld from PATH)",
    )
    parser.add_argument(
        "--xtrabackup",
        help="Override path to xtrabackup binary",
    )
    return parser.parse_args(argv)


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


def get_xtrabackup_binary(db_major: str) -> Path:
    match db_major:
        case "5.6":
            return Path("/opt/xtrabackup-2.4/bin/xtrabackup")
        case "5.7":
            return Path("/opt/xtrabackup-2.4/bin/xtrabackup")
        case "8.0":
            return Path("/opt/xtrabackup-8.0/bin/xtrabackup")
        case "8.4":
            return Path("/opt/xtrabackup-8.4/bin/xtrabackup")
        case "9.7":
            return Path("/opt/xtrabackup-9.7/bin/xtrabackup")
        case _:
            raise RuntimeError(f"Unsupported MySQL version: {db_major}")


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
        db_version, db_major = get_mysql_version(args.mysqld)

        if args.xtrabackup:
            xb_path = Path(args.xtrabackup)
        else:
            xb_path = get_xtrabackup_binary(db_major)

        xb_version = get_xtrabackup_version(xb_path)

    except (FileNotFoundError, RuntimeError) as exc:
        OUTPUT.write_text(f"hello world from xbo: {now}\nERROR: {exc}\n")
        return 1

    OUTPUT.write_text(
        f"hello world from xbo: {now}\n"
        f"mysql: {db_version}\n"
        f"mysqld: {args.mysqld}\n"
        f"xtrabackup: {xb_path}\n"
        f"xtrabackup version: {xb_version}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
