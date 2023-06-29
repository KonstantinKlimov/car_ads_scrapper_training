if not exists (select * from sys.databases where name = 'car_ads_training_db')
begin
    create database car_ads_training_db;
end;
go

use car_ads_training_db;
go

if object_id('ads') is null
begin
    create table ads
    (
        ads_id                       int not null primary key identity,

        source_id                    nvarchar(100) not null,
        card_url                     nvarchar(255) not null,
        ad_group_id                  int not null,
        insert_process_log_id        int not null,
        insert_date                  datetime not null default getdate(),
        change_status_process_log_id int,
        ad_status                    smallint not null default 0,
        change_status_date           datetime,
        card                         nvarchar(max)
    );
end;
go

if object_id('ad_groups') is null
begin
    create table ad_groups
    (
        ad_group_id         int not null primary key identity,

        group_url           nvarchar(255) not null,
        process_log_id      int not null,
        insert_date         datetime not null default getdate()
    );
end;
go

if object_id('process_log') is null
begin
    create table process_log
    (
        process_log_id      int not null primary key identity,

        process_desc        nvarchar(255) not null,
        [user]              nvarchar(255) not null,
        [host]              nvarchar(255) not null,
        connection_id       int,
        start_date          datetime not null default getdate(),
        end_date            datetime
    );
end;
go