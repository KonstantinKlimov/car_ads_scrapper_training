-- use test_db;

insert into process_log(process_desc, user, host, connection_id)
select 'datafix_ad_groups_tokenize_group_url_with_the_help_of_cursor.sql',
	   user,
	   host,
	   connection_id()
from information_schema.processlist
where id = connection_id();

set @process_log_id := last_insert_id();

-- make a "backup"
drop table if exists ad_groups_bak;

create table ad_groups_bak (ad_group_id int not null primary key auto_increment) as
select ad_group_id, group_url, process_log_id, insert_date from ad_groups;

-- add new columns. default values will be updated later with real values
alter table ad_groups add price_min int default -1;
alter table ad_groups add page_size tinyint default -1;
alter table ad_groups add year smallint default -1;
alter table ad_groups add page_num smallint default -1;

-- create procedure transforming ad_groups table
drop procedure if exists usp_tokenize_group_url;

delimiter //

create procedure usp_tokenize_group_url()
begin
  declare finished integer default 0;
  declare id integer;
  declare url varchar(255);

  declare cur_group_url cursor for select ad_group_id, group_url from ad_groups;


  -- declare not found handler
  declare continue handler for not found set finished = 1;

  open cur_group_url;

  while_loop:
  while True do
    fetch cur_group_url into id, url;

    if finished = 1 then
        leave while_loop;
    end if;

    set @args = substring_index(url, '?', -1);
    set @args_json = concat('{"', replace(replace(@args, '&', '", "'), '=', '": "'), '"}');

    select year, page_size, page_num, price_min
		into @year, @page_size, @page_num, @price_min
        from json_table(@args_json, '$'
			  columns (
				year smallint path '$.year_min',
				page_size tinyint path '$.page_size',
				page_num smallint path '$.page',
				price_min int path '$.list_price_min'
			  )
			) as jt;

	update ad_groups
		set year = @year,
			page_size = @page_size,
			page_num = @page_num,
			price_min = @price_min
	where ad_group_id =  id;

  end while;

  close cur_group_url;
end; //

delimiter ;
;

-- execute procedure to populate recently added fields
call usp_tokenize_group_url();

-- drop procedure as it is not needed anymore
drop procedure usp_tokenize_group_url;

-- remove unneeded field and complete transition from old to new model
alter table ad_groups drop group_url;

-- make new fields just not null, without defaults
-- alter table ad_groups modify column price_min int not null;
-- alter table ad_groups modify column page_size tinyint not null;
-- alter table ad_groups modify column year smallint not null;
-- alter table ad_groups modify column page_num smallint not null;

update process_log
  set end_date = current_timestamp()
where process_log_id = @process_log_id;
