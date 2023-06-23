set global general_log = 0;

set global slow_query_log = 1;
set global long_query_time = 0;
set global log_queries_not_using_indexes = 1;

set global log_output = 'TABLE';

truncate table mysql.general_log;
truncate table mysql.slow_log;

-- set global log_output = 'FILE';
-- set global general_log_file = '/var/lib/mysql/mysql.log';

-- show variables like '%log%';
--
-- select * from mysql.general_log;
-- select * from mysql.slow_log;