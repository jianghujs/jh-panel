PRAGMA synchronous = 0;
PRAGMA page_size = 4096;
PRAGMA journal_mode = wal;
PRAGMA journal_size_limit = 1073741824;
CREATE TABLE IF NOT EXISTS `project` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `name` TEXT,
    `path` TEXT,
    `start_script` TEXT,
    `reload_script` TEXT,
    `stop_script` TEXT,
    `autostart_script` TEXT,
    `echo` TEXT,
    `create_time` INTEGER
);
