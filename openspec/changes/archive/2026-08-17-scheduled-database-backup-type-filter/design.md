## Context

Scheduled database backup tasks currently store the selected database in the existing `sname` field. Recent PostgreSQL backup support added type-prefixed single database values (`mysql:<db>` and `postgresql:<db>`), but the UI still exposes a single bare `backupAll` option. Bare `backupAll` is also used by existing scheduled tasks and currently runs both MySQL and PostgreSQL backups for compatibility.

The change must let operators limit a new scheduled task to MySQL, PostgreSQL, or both without requiring legacy task recreation. It must also keep MySQL-only settings such as `mysqldump`/`mydumper` out of PostgreSQL-only tasks.

## Goals / Non-Goals

**Goals:**

- Let the scheduled task database selector filter database rows by checked database plugin types.
- Make newly saved all-database tasks persist an explicit database-type scope.
- Preserve the current behavior of existing bare `backupAll` tasks.
- Keep implementation within existing scheduled-task fields and backup scripts.

**Non-Goals:**

- Add a new crontab table column or migrate existing task rows.
- Add physical full-cluster PostgreSQL backup similar to xtrabackup.
- Change single database backup file naming or restore behavior.
- Change backup retention semantics.

## Decisions

### Encode backup scope in `sname`

Use explicit `sname` values for new all-database tasks:

- `mysql:backupAll` for all MySQL databases.
- `postgresql:backupAll` for all PostgreSQL databases.
- `all:backupAll` for all supported database plugin types selected together.
- Bare `backupAll` remains the legacy all-types value.

This avoids a schema migration and keeps schedule execution driven by the existing fields. The alternative was adding a separate scope column, but that would require a migration path and extra compatibility logic for little benefit.

### Add an explicit MySQL-only script entry point

Add a `mysql_database` command type to `/www/server/jh-panel/scripts/backup.py` for MySQL-only backups. Keep the existing `database backupAll` behavior unchanged for legacy tasks.

This separates new precise semantics from the compatibility behavior. The alternative was redefining `database backupAll` as MySQL-only, but that would silently change old task behavior.

### Filter database list in the scheduled-task UI

The database backup form should render MySQL and PostgreSQL checkboxes when those plugin database lists are available. The visible database dropdown should include only databases whose `db_type` matches checked types. The synthetic "all databases" option should compute its value from the selected types.

The backend can optionally accept a database-type filter for `/crontab/get_data_list`, but the frontend can also filter the combined response locally. Keeping backend metadata in each item (`db_type`, `raw_name`) is required for editing and display.

### Hide dump method for PostgreSQL-only scope

Show `mysqldump`/`mydumper` only when the selected scope includes MySQL. PostgreSQL-only tasks should submit an empty dump type because PostgreSQL backup uses its own plugin tooling.

## Risks / Trade-offs

- Existing edited tasks using bare `backupAll` may display as both database types selected -> Preserve bare `backupAll` on unchanged edit where possible, or treat it as equivalent to both types without changing execution semantics.
- Empty checkbox selection could produce an invalid task -> Require at least one database type before saving or automatically restore the previous checked type.
- Sites without one database plugin installed could show confusing controls -> Render only available plugin types and default to the installed types.
- Combined all-types command can partially succeed if one engine fails -> Execute commands sequentially with shell `set -e` behavior consistent with current scheduled task scripts, and surface output in the task log.

## Migration Plan

- No data migration is required.
- Existing rows with `sname=backupAll` continue to call the compatibility backup path.
- New or edited rows use explicit type-scoped `sname` values.
- Rollback can keep legacy `backupAll` tasks working; only newly created type-scoped rows would need to be edited back to a supported value if code is reverted.

## Open Questions

- Whether the UI label for both selected types should be "全部数据库" or "MySQL + PostgreSQL 所有数据库". The implementation should prefer a clear operator-facing label.
