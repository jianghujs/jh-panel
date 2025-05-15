CREATE TABLE IF NOT EXISTS `network` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `up` INTEGER,
  `down` INTEGER,
  `total_up` INTEGER,
  `total_down` INTEGER,
  `down_packets` INTEGER,
  `up_packets` INTEGER,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `cpuio` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `pro` INTEGER,
  `mem` INTEGER,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `diskio` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `read_count` INTEGER,
  `write_count` INTEGER,
  `read_bytes` INTEGER,
  `write_bytes` INTEGER,
  `read_time` INTEGER,
  `write_time` INTEGER,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `database` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `total_size` INTEGER,
  `total_bytes` INTEGER,
  `list` TEXT,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `load_average` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `pro` REAL,
  `one` REAL,
  `five` REAL,
  `fifteen` REAL,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `directory_size` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `path` TEXT,
  `size` INTEGER DEFAULT 0,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `disk_usage` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `path` TEXT,
  `total` INTEGER DEFAULT 0,
  `used` INTEGER DEFAULT 0,
  `free` INTEGER DEFAULT 0,
  `percent` REAL DEFAULT 0,
  `addtime` INTEGER
);