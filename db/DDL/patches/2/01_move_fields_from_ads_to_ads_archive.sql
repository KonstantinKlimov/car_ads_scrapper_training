-- use car_ads_training_db;

insert into process_log(process_desc, user, host, connection_id)
select 'datafix_move_fields_from_ads_to_ads_archive.sql',
	   user,
	   host,
	   connection_id()
from information_schema.processlist
where id = connection_id();

set @process_log_id := last_insert_id();

-- drop table if exists ads_archive;

create table if not exists ads_archive
(
    ads_archive_id               int not null primary key auto_increment,

	ads_id                       int not null,
    source_id                    varchar(100) not null,
    card_url                     varchar(255) not null,
    ad_group_id                  int not null,
    process_log_id               int,
    ad_status                    tinyint not null default 0,
    modify_date                  datetime,
    card                         json
) character set utf8mb3;

-- copy finder's records to the archive table
insert into ads_archive
(
    ads_id,
    source_id,
    card_url,
    ad_group_id,
    process_log_id,
    ad_status,
    modify_date,
    card
)
select
    ads.ads_id,
    ads.source_id,
    ads.card_url,
    ads.ad_group_id,
    ads.insert_process_log_id,
    0 as ad_status,
    ads.insert_date,
    null as card
from ads
left join ads_archive on ads.ads_id = ads_archive.ads_id and ads_archive.modify_date = ads.insert_date
where ads_archive.ads_id is null;

-- copy scrapper's records to the archive table
insert into ads_archive
(
    ads_id,
    source_id,
    card_url,
    ad_group_id,
    process_log_id,
    ad_status,
    modify_date,
    card
)
select
    ads.ads_id,
    ads.source_id,
    ads.card_url,
    ads.ad_group_id,
    ads.change_status_process_log_id,
    ads.ad_status,
    ads.change_status_date,
    ads.card
from ads
left join ads_archive on ads.ads_id = ads_archive.ads_id and ads_archive.modify_date = ads.change_status_date
where ads.ad_status <> 0 and
      JSON_VALID(ads.card) = 1 and
      ads_archive.ads_id is null;

-- "backup" ads table
-- drop table if exists ads_bak;

create table if not exists ads_bak(ads_id int not null primary key auto_increment) as
select * from ads where 1 = 0;


insert into ads_bak
(
    ads_id,
    source_id,
    card_url,
    ad_group_id,
    insert_process_log_id,
    insert_date,
    change_status_process_log_id,
    ad_status,
    change_status_date,
    card
)
select
    ads.ads_id,
    ads.source_id,
    ads.card_url,
    ads.ad_group_id,
    ads.insert_process_log_id,
    ads.insert_date,
    ads.change_status_process_log_id,
    ads.ad_status,
    ads.change_status_date,
    ads.card
from ads
left join ads_bak on ads.ads_id = ads_bak.ads_id -- and ifnull(ads.change_status_date, ads.insert_date) = ifnull(ads_bak.change_status_date, ads_bak.insert_date)
where ads_bak.ads_id is null;

-- remove card field
-- be carefull! make sure the backup table is created and populated
alter table ads drop ad_group_id;
alter table ads drop insert_process_log_id;
alter table ads drop insert_date;
alter table ads drop change_status_process_log_id;
alter table ads drop ad_status;
alter table ads drop change_status_date;
alter table ads drop card;                             -- takes time, because table's pages (leaf level) are rebuilt (actually the table itself is recreated)

update process_log
  set end_date = current_timestamp()
where process_log_id = @process_log_id;


-- select count(*) from ads;
-- select count(*) from ads_archive;
