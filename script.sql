create table `group`
(
    组id         int auto_increment
        primary key,
    组名         varchar(255) null,
    工作日志标准 text null,
    管理员组     varchar(255) null,
    用户组       varchar(255) null
);

create table user
(
    id              int auto_increment
        primary key,
    uuid            varchar(32)  not null,
    name            varchar(32) null,
    role            varchar(32) collate utf8mb4_bin null,
    hashed_password varchar(255) not null,
    create_datetime datetime default CURRENT_TIMESTAMP null,
    update_datetime datetime default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP,
    last_login      datetime default CURRENT_TIMESTAMP null,
    active          tinyint(1)                         null,
    constraint uuid
        unique (uuid)
);

create index idx_user_id
    on user (id);

create index idx_user_uuid
    on user (uuid);

create table worklog
(
    id       int auto_increment
        primary key,
    姓名     text null,
    时间     time null,
    工作日志 text null,
    active   tinyint(1)   null,
    向量     blob null,
    uuid     varchar(255) null
);

create index idx_worklog_id
    on worklog (id);


