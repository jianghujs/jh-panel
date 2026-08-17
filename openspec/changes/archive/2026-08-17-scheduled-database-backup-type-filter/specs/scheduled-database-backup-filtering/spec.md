## ADDED Requirements

### Requirement: Database backup tasks expose database type filters
The scheduled task database backup form SHALL provide selectable database plugin type filters for installed MySQL and PostgreSQL database sources.

#### Scenario: Filter by MySQL only
- **WHEN** an operator selects only the MySQL database type filter
- **THEN** the database dropdown SHALL show MySQL databases and the all-database option SHALL target only MySQL databases

#### Scenario: Filter by PostgreSQL only
- **WHEN** an operator selects only the PostgreSQL database type filter
- **THEN** the database dropdown SHALL show PostgreSQL databases and the all-database option SHALL target only PostgreSQL databases

#### Scenario: Filter by multiple database types
- **WHEN** an operator selects both MySQL and PostgreSQL database type filters
- **THEN** the database dropdown SHALL show databases from both selected types and the all-database option SHALL target both selected types

### Requirement: All-database backup scope is persisted explicitly for new tasks
New scheduled database backup tasks SHALL persist all-database scope using a database-type-aware `sname` value.

#### Scenario: Save MySQL all-database task
- **WHEN** an operator creates a database backup task with only MySQL selected and chooses all databases
- **THEN** the saved task SHALL identify the target as all MySQL databases without targeting PostgreSQL databases

#### Scenario: Save PostgreSQL all-database task
- **WHEN** an operator creates a database backup task with only PostgreSQL selected and chooses all databases
- **THEN** the saved task SHALL identify the target as all PostgreSQL databases without targeting MySQL databases

#### Scenario: Save all selected database types task
- **WHEN** an operator creates a database backup task with MySQL and PostgreSQL selected and chooses all databases
- **THEN** the saved task SHALL identify the target as all selected database types

### Requirement: Scheduled execution respects database type scope
Scheduled database backup execution SHALL run only the database engines represented by the task target scope.

#### Scenario: Execute MySQL-only all-database task
- **WHEN** a scheduled task target is all MySQL databases
- **THEN** the generated backup script SHALL execute MySQL database backup logic only

#### Scenario: Execute PostgreSQL-only all-database task
- **WHEN** a scheduled task target is all PostgreSQL databases
- **THEN** the generated backup script SHALL execute PostgreSQL database backup logic only

#### Scenario: Execute all-types all-database task
- **WHEN** a scheduled task target is all supported database types
- **THEN** the generated backup script SHALL execute MySQL and PostgreSQL database backup logic

### Requirement: Legacy all-database tasks remain compatible
Existing scheduled database backup tasks that use the legacy bare `backupAll` target SHALL continue to execute with the established compatibility behavior.

#### Scenario: Execute legacy backupAll task
- **WHEN** a scheduled database backup task has `sname` equal to bare `backupAll`
- **THEN** the task SHALL continue to run the compatibility all-database backup path without requiring the task to be recreated

#### Scenario: Edit legacy backupAll task
- **WHEN** an operator opens an existing database backup task with bare `backupAll`
- **THEN** the form SHALL represent it as an all-database backup across the available database types

### Requirement: MySQL dump method is shown only when applicable
The scheduled task form SHALL show MySQL dump method selection only when the current database backup scope includes MySQL.

#### Scenario: PostgreSQL-only scope hides dump method
- **WHEN** the selected database backup scope includes only PostgreSQL
- **THEN** the form SHALL hide MySQL dump method controls and SHALL submit no MySQL dump method value

#### Scenario: MySQL scope shows dump method
- **WHEN** the selected database backup scope includes MySQL
- **THEN** the form SHALL show MySQL dump method controls and SHALL submit the selected MySQL dump method value
