create database if not exists car_ads_training_db;

use car_ads_training_db;

create table if not exists ads
(
    ads_id                      int not null primary key auto_increment,

    source_id                   varchar(100) not null,
    card_url                    varchar(255) not null
) character set utf8mb3;

create table if not exists ad_groups
(
    ad_group_id                 int not null primary key auto_increment,

    price_min                   int not null default -1,
    page_size                   tinyint not null default -1,
    year                        smallint not null default -1,
    page_num                    smallint not null default -1,

    process_log_id              int not null,
    insert_date                 datetime not null default current_timestamp
) character set utf8mb3;

create table if not exists process_log
(
    process_log_id              int not null primary key auto_increment,

    process_desc                varchar(255) not null,
    `user`                      varchar(255) not null,
    host                        varchar(255) not null,
    connection_id               int,
    start_date                  datetime not null default current_timestamp,
    end_date                    datetime
) character set utf8mb3;

create table if not exists ads_archive
(
    ads_archive_id              int not null primary key auto_increment,

	ads_id                      int not null,
    source_id                   varchar(100) not null,
    card_url                    varchar(255) not null,
    ad_group_id                 int not null,
    process_log_id              int,
    ad_status                   tinyint not null default 0,
    modify_date                 datetime not null default current_timestamp,
    card                        json
) character set utf8mb3;

