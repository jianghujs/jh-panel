## 1. Plugin Skeleton

- [x] 1.1 Create `plugins/ha_manager/` with `info.json`, `index.py`, `index.html`, `install.sh`, icon placeholder and `js/ha_manager.js` following existing plugin conventions.
- [x] 1.2 Add helper functions for plugin path, server data path `/www/server/ha_manager/`, config path and argument parsing.
- [x] 1.3 Implement install-time directory creation and safe default config initialization.

## 2. Configuration And SSH Key Management

- [x] 2.1 Implement config load/save helpers for `/www/server/ha_manager/config.json` with defaults for connection status, switch state and check results.
- [x] 2.2 Implement validation for `relation_id`, `peer_ip`, `ssh_user`, `ssh_port`, `peer_ssh_public_key` and `configured_role`.
- [x] 2.3 Implement SSH key generation for `/root/.ssh/ha_manager` and `/root/.ssh/ha_manager.pub` with correct directory and file permissions.
- [x] 2.4 Implement public key read API for the page.
- [x] 2.5 Implement authorized key insertion that appends `peer_ssh_public_key` to `/root/.ssh/authorized_keys` without duplicates.

## 3. Status And Peer Checks

- [x] 3.1 Implement `get_status --local-only` with local config, switch state and mysql-apt status checks.
- [x] 3.2 Implement mysql-apt check by calling `python3 plugins/mysql-apt/index.py get_master_status` and mapping failures to structured check results.
- [x] 3.3 Implement full `get_status` that includes peer SSH status unless `--local-only` is present.
- [x] 3.4 Implement peer SSH test using `/root/.ssh/ha_manager`, configured SSH user, port and peer IP.
- [x] 3.5 Map peer failures to `ssh_timeout`, `ssh_auth_failed`, `peer_plugin_missing` and `relation_id_mismatch`.
- [x] 3.6 Implement one-primary-one-standby validation and switching timeout detection.

## 4. Switch Role Command

- [x] 4.1 Implement `switch_role switching` to write `switch_state=switching` and `switch_started_at`.
- [x] 4.2 Implement `switch_role primary` and `switch_role standby` to update `configured_role` and reset `switch_state=normal`.
- [x] 4.3 Implement `switch_role failed` to write failure state and timestamp.
- [x] 4.4 Reject invalid `switch_role` arguments without modifying config.

## 5. Frontend Page

- [x] 5.1 Build plugin page menu for relation config, connection status and self-check result.
- [x] 5.2 Render local public key, config form and save/test buttons.
- [x] 5.3 Render connection status, last peer result, local checks and summary status.
- [x] 5.4 Add refresh actions for config, peer test and self-check.

## 6. Verification

- [x] 6.1 Run Python syntax checks for new plugin scripts.
- [x] 6.2 Verify config save rejects invalid roles and missing required fields.
- [x] 6.3 Verify SSH key generation creates expected files with safe permissions.
- [x] 6.4 Verify `get_status --local-only` returns valid JSON when mysql-apt exists and when mysql-apt is missing.
- [x] 6.5 Verify `switch_role` transitions update `config.json` as specified.
