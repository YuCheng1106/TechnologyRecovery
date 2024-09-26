create table `group`
(
    id               int auto_increment
        primary key,
    uuid             varchar(32)                          not null,
    name             varchar(255)                         not null,
    description      text                                 null,
    create_datetime  datetime   default CURRENT_TIMESTAMP null,
    update_datetime  datetime   default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP,
    active           tinyint(1) default 1                 null,
    worklog_standard text                                 null,
    admin_users      text                                 null,
    user_users       text                                 null,
    constraint uuid
        unique (uuid)
);

create index idx_group_id
    on `group` (id);

create index idx_group_uuid
    on `group` (uuid);

create table user
(
    id              int auto_increment
        primary key,
    uuid            varchar(32)                                      not null,
    name            varchar(32)                                      null,
    email           varchar(255)                                     null,
    avatar          varchar(255)                                     null,
    introduction    text                                             null,
    hashed_password varchar(255)                                     not null,
    create_datetime datetime               default CURRENT_TIMESTAMP null,
    update_datetime datetime               default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP,
    last_login      datetime               default CURRENT_TIMESTAMP null,
    active          tinyint(1)                                       null,
    role            enum ('admin', 'user') default 'user'            null,
    constraint email
        unique (email),
    constraint uuid
        unique (uuid)
);

create index idx_user_email
    on user (email);

create index idx_user_id
    on user (id);

create index idx_user_uuid
    on user (uuid);

create table worklog
(
    id              int auto_increment
        primary key,
    uuid            varchar(32)                        not null,
    user_uuid       varchar(32)                        not null,
    group_uuid      varchar(32)                        not null,
    content         text                               null,
    task            text                               null,
    solution        text                               null,
    effect          text                               null,
    create_datetime datetime default CURRENT_TIMESTAMP null,
    update_datetime datetime default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP,
    active          tinyint(1)                         null,
    embedding       blob                               null,
    constraint uuid
        unique (uuid)
);

create index idx_worklog_id
    on worklog (id);

create index idx_worklog_uuid
    on worklog (uuid);


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