mysqldump -utimoti -penter1 --lock-tables=0 mysql slow_log > slow_log.sql
mysqldump -utimoti -penter1 --lock-tables=0 mysql general_log > general_log.sql
