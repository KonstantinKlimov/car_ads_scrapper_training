-- use car_ads_training_db;

-- takes time as there is a table scan + update
alter table ads_archive modify column modify_date datetime not null default current_timestamp;
