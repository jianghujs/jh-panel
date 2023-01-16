PRAGMA synchronous = 0;
PRAGMA page_size = 4096;
PRAGMA journal_mode = wal;
PRAGMA journal_size_limit = 1073741824;
CREATE TABLE IF NOT EXISTS `script` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `name` TEXT,
    `script` TEXT,
    `echo` TEXT,
    `create_time` INTEGER
);

