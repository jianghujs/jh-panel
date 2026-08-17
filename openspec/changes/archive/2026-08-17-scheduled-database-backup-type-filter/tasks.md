## 1. Backend Scope Parsing and Script Generation

- [x] 1.1 Extend database target parsing to recognize `mysql:backupAll`, `postgresql:backupAll`, `all:backupAll`, bare legacy `backupAll`, and bare legacy MySQL database names.
- [x] 1.2 Update scheduled database backup shell generation so MySQL-only, PostgreSQL-only, all-types, and legacy all-database targets execute the correct backup commands.
- [x] 1.3 Preserve existing single database command generation for `mysql:<db>`, `postgresql:<db>`, and legacy bare MySQL database names.

## 2. Backup Script Dispatch

- [x] 2.1 Add a `mysql_database` command type in `/www/server/jh-panel/scripts/backup.py` that executes MySQL database backup logic only.
- [x] 2.2 Keep existing `database backupAll` behavior as the legacy compatibility path that backs up MySQL and PostgreSQL.
- [x] 2.3 Ensure database backup cleanup still runs for new MySQL-only and PostgreSQL-only command paths.

## 3. Scheduled Task Database UI

- [x] 3.1 Add MySQL and PostgreSQL type checkboxes to the database backup task form when the corresponding database source is available.
- [x] 3.2 Filter the database dropdown by checked database types and prevent saving when no database type is selected.
- [x] 3.3 Compute the all-database dropdown value from selected types: MySQL-only, PostgreSQL-only, or all selected types.
- [x] 3.4 Update task name display so all-database tasks clearly show the selected database scope.

## 4. Edit Task Compatibility

- [x] 4.1 Initialize database type checkboxes correctly when editing `backupAll`, `mysql:backupAll`, `postgresql:backupAll`, `all:backupAll`, type-prefixed single database, and legacy bare database tasks.
- [x] 4.2 Keep legacy bare `backupAll` tasks executable without requiring the operator to recreate them.
- [x] 4.3 Ensure changing the database type filters during edit refreshes the database dropdown and target value consistently.

## 5. Dump Method Behavior

- [x] 5.1 Show `mysqldump`/`mydumper` controls only when the selected target scope includes MySQL.
- [x] 5.2 Submit an empty dump method for PostgreSQL-only tasks and preserve the selected dump method for MySQL-including tasks.

## 6. Verification

- [x] 6.1 Verify new MySQL-only all-database scheduled task generates a MySQL-only backup command.
- [x] 6.2 Verify new PostgreSQL-only all-database scheduled task generates a PostgreSQL-only backup command.
- [x] 6.3 Verify new all-types all-database scheduled task generates both MySQL and PostgreSQL backup commands.
- [x] 6.4 Verify an existing bare `backupAll` task still executes without being recreated.
- [x] 6.5 Verify single database selections for MySQL and PostgreSQL still generate the expected backup commands.
