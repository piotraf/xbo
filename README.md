# xbo

Percona Xtrabackup wrapper and backup orchestrator, driven per-instance by environment files.

## Status

Early development — not usable at all yet. placeholder script.

## Scope

- Pre-flight checks: instance liveness, datadir size, free-space validation (backup + compression)
- Backup and compression execution (Percona XtraBackup 8.4 / MySQL 8.4)
- Writes current-backup pointer file for downstream restore/refresh automation
- Records run metrics (datadir size, backup/compression duration)

## Requirements

- RHEL 8.10+ (python3.12, python3.12-PyMySQL)
- percona-xtrabackup-8.4

## License

MIT
