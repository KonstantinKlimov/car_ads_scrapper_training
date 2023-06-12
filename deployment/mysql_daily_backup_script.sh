#!/bin/bash
sudo mysqldump -h data-server-vm -u timoti -penter1 car_ads_training_db > /mnt/disk-for-data/backup/car_ads_training_db-$(date "+%Y%m%d").sql