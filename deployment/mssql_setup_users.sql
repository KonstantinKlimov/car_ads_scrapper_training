create login timoti with password = 'enter1'
go

use car_ads_training_db
go

create user timoti for login timoti;
go

exec sp_addrolemember 'db_owner', 'timoti'
go
