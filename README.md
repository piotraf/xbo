# xbo

Percona XtraBackup wrapper and backup orchestrator, driven per-instance by environment files.

## Status

Early development (0.x = alpha) — placeholder logic; the layout, CI and release pipeline are real.

## Install

| Way | Command |
|---|---|
| pipx / uv (dev, lab) | `pipx install git+https://github.com/piotraf/xbo` |
| single file (curl-and-run) | download `xbo` from the [latest release](https://github.com/piotraf/xbo/releases/latest), `chmod +x xbo` |
| rpm (customers, OL8/9) | planned |

```
xbo --version
xbo                                   # mysqld from PATH, xtrabackup chosen by MySQL version
xbo --instance prod84                 # from config.toml
xbo --mysqld /path/mysqld --xtrabackup /path/xtrabackup --my-cnf /path/my.cnf
```

## Configuration

TOML, lowest → highest precedence: `/etc/xbo/config.toml` → `~/.config/xbo/config.toml` →
`--config PATH` → CLI flags (`--mysqld`, `--xtrabackup`, `--my-cnf`).

```toml
mysqld = "mysqld"                       # default binary (from PATH)

[xtrabackup]                            # MySQL major -> xtrabackup binary
"5.7" = "/opt/xtrabackup-2.4/bin/xtrabackup"
"8.4" = "/opt/xtrabackup-8.4/bin/xtrabackup"

[instance.prod84]                       # xbo --instance prod84
mysqld = "/mysqlbin/mysql-8.4.6/bin/mysqld"
my_cnf = "/db/84/my.cnf"
```

## Scope

- Pre-flight checks: instance liveness, datadir size, free-space validation (backup + compression)
- Backup and compression execution (Percona XtraBackup 8.4 / MySQL 8.4)
- Writes current-backup pointer file for downstream restore/refresh automation
- Records run metrics (datadir size, backup/compression duration)

## Requirements

- RHEL 8.10+ (python3.12, python3.12-PyMySQL)
- percona-xtrabackup-8.4

## Development

```
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check . && .venv/bin/pytest
```

Branch → PR → CI green (runs on the lab's cidb01) → squash-merge. Releases are cut by
release-please from Conventional Commits (`feat:`, `fix:`): merge its release PR and the
tag, GitHub Release and standalone `xbo` file appear.

## License

MIT
