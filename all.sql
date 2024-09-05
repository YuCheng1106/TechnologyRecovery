CREATE USER 'tech_user'@'localhost' IDENTIFIED BY 'tech_password';

CREATE DATABASE `TechnologyRecovery` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON TechnologyRecovery.* TO 'tech_user'@'localhost';

CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(32),
    email VARCHAR(255) UNIQUE NOT NULL,
    avatar VARCHAR(255),
    introduction TEXT,
    hashed_password VARCHAR(255) NOT NULL,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_datetime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN,
    role ENUM('admin', 'user') DEFAULT 'user',
    INDEX idx_user_uuid (uuid),
    INDEX idx_user_email (email),
    INDEX idx_user_id (id)
);

ALTER TABLE user
ADD COLUMN role ENUM('admin', 'user') DEFAULT 'user';


CREATE TABLE workLog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(32) UNIQUE NOT NULL,
    user_uuid VARCHAR(32) NOT NULL,
    group_uuid VARCHAR(32) NOT NULL,
    content TEXT,
    task TEXT,
    solution TEXT,
    effect TEXT,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_datetime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN,
    INDEX idx_worklog_uuid (uuid),
    INDEX idx_worklog_id (id)
);

ALTER TABLE workLog
ADD COLUMN group_uuid VARCHAR(32);

ALTER TABLE workLog
ADD COLUMN content TEXT;

ALTER TABLE workLog
ADD COLUMN embedding BLOB;


CREATE TABLE `group` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_datetime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    INDEX idx_group_uuid (uuid),
    INDEX idx_group_id (id)
);

CREATE TABLE user_group (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_uuid VARCHAR(32) NOT NULL,
    group_uuid VARCHAR(32) NOT NULL,
    role ENUM('creator', 'admin', 'member') DEFAULT 'member',
    join_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_group_user_uuid (user_uuid),
    INDEX idx_user_group_group_uuid (group_uuid),
    FOREIGN KEY (user_uuid) REFERENCES user(uuid) ON DELETE CASCADE,
    FOREIGN KEY (group_uuid) REFERENCES `group`(uuid) ON DELETE CASCADE
);
