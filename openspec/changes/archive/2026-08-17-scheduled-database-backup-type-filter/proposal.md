## Why

The scheduled database backup task currently has one ambiguous "all databases" option, so after PostgreSQL support was added an existing-looking task can unintentionally back up both MySQL and PostgreSQL. Operators need to choose which database plugin types are in scope without rebuilding legacy tasks.

## What Changes

- Add database-type selection to the scheduled database backup UI, with MySQL and PostgreSQL checkboxes controlling the database list.
- Make "all databases" scoped to the checked database types for newly created or edited tasks.
- Persist database backup scope in `sname` using explicit type-aware values such as `mysql:backupAll`, `postgresql:backupAll`, and an all-types value.
- Keep legacy scheduled tasks using bare `backupAll` compatible with their current behavior.
- Ensure PostgreSQL-only scheduled backups do not show or require MySQL dump method settings.

## Capabilities

### New Capabilities
- `scheduled-database-backup-filtering`: Scheduled database backup tasks can filter database choices and all-database execution by database plugin type.

### Modified Capabilities

None.

## Impact

- Affects the scheduled task database backup form in `/www/server/jh-panel/route/static/app/crontab.js`.
- Affects scheduled task database list and script generation in `/www/server/jh-panel/class/core/crontab_api.py`.
- Affects database backup command dispatch in `/www/server/jh-panel/scripts/backup.py`.
- No database schema change is expected; existing `sname` and `sbody` fields remain in use.
