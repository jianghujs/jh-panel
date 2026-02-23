## ADDED Requirements
### Requirement: Record History Cleanup Script
The system SHALL provide a CLI script in the VM OS tools that analyzes tables matching `_record_history`, estimates cleanup impact, generates cleanup SQL, and only executes the SQL after explicit user confirmation. The script SHALL prompt for database connection details, allow selecting databases to include, and support a retention window based on a time column with sensible defaults and user override.

#### Scenario: Generate SQL without execution
- **WHEN** the operator selects a retention window and declines execution
- **THEN** the script generates and saves cleanup SQL without running it

#### Scenario: Confirm execution after review
- **WHEN** the operator reviews the generated cleanup SQL and confirms execution
- **THEN** the script executes the SQL against the selected databases
