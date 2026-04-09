# Change: Add record_history cleanup analysis script

## Why
_record_history tables can grow quickly and are hard to clean safely. We need a guided script that estimates impact, generates cleanup SQL, and only runs after explicit confirmation.

## What Changes
- Add a new OS tool script to analyze `_record_history` tables and generate cleanup SQL.
- Require explicit confirmation before executing cleanup SQL.
- Add a new menu entry under `index__arrange.sh` to run the script.

## Impact
- Affected specs: `specs/mysql-record-history-cleanup/spec.md` (new)
- Affected code: `scripts/os_tool/vm/default/index__arrange.sh`, new script under `scripts/os_tool/vm/default/`
