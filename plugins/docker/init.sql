PRAGMA synchronous = 0;
PRAGMA page_size = 4096;
PRAGMA journal_mode = wal;
PRAGMA journal_size_limit = 1073741824;
CREATE TABLE IF NOT EXISTS `repository` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `user_name` TEXT,
    `user_pass` TEXT,
    `registry` TEXT,
    `hub_name` TEXT,
    `namespace` TEXT,
    `repository_name` TEXT,
    `create_time` INTEGER
);
