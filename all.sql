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
    INDEX idx_user_uuid (uuid),
    INDEX idx_user_email (email),
    INDEX idx_user_id (id)
);

CREATE TABLE workLog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(32) UNIQUE NOT NULL,
    user_uuid VARCHAR(32) NOT NULL,
    task TEXT,
    solution TEXT,
    effect TEXT,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_datetime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN,
    INDEX idx_worklog_uuid (uuid),
    INDEX idx_worklog_id (id)
);
