
# sudo google_metadata_script_runner startup

# in case we haven't used that external disk previously, we need to format it
# sudo mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/sdb

if [ ! -f /soft/car_ads_scrapper_training/data-server-vm-configured ]; then
    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Mounting external data disk"
    echo
    sudo mkdir -p /mnt/disk-for-data
    echo UUID=`sudo blkid -s UUID -o value /dev/sdb` /mnt/disk-for-data/ ext4 discard,defaults,nofail 0 2 | sudo tee -a /etc/fstab
    sudo mount -o discard,defaults /dev/sdb /mnt/disk-for-data
    sudo chmod a+w /mnt/disk-for-data/
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Creating data folders"
    echo
    sudo mkdir -p /mnt/disk-for-data/mysql
    sudo mkdir -p /mnt/disk-for-data/car_ads_scrapper_training
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Installing docker subsystem"
    echo
    sudo apt update
    sudo apt install --yes docker.io
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Pulling mysql-server:8.0 docker image"
    echo
    sudo docker image pull mysql/mysql-server:8.0
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Starting mysql-server:8.0 docker container"
    echo
    sudo docker run --name mysql --restart=always -p 3306:3306 -v /mnt/disk-for-data/mysql:/var/lib/mysql/ -d -e "MYSQL_ROOT_PASSWORD=enter1" mysql/mysql-server:8.0
    sleep 30
    echo
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Installing java"
    echo
    sudo apt install --yes openjdk-8-jre-headless
    export JAVA_HOME=/usr
    echo "JAVA_HOME=/usr" | sudo tee -a /etc/environment
    source /etc/environment

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Creating a swap file (1GB)"
    echo
    sudo mkdir -v /mnt/disk-for-data/swap
    cd /mnt/disk-for-data/swap
    sudo dd if=/dev/zero of=swapfile bs=1K count=1M

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Enabling swapping"
    echo
    sudo chmod 600 swapfile
    sudo mkswap swapfile
    sudo swapon swapfile

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Adding record to /etc/fstab for automounting swap file"
    echo
    echo "/mnt/disk-for-data/swap/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Cloning github repository"
    echo
    sudo mkdir /soft
    sudo git clone https://github.com/timoti1/car_ads_scrapper_training /soft/car_ads_scrapper_training
    echo
    echo

    # set the rdbms up
    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Creating database (mysql) objects"
    echo
    sudo docker exec -i mysql mysql -uroot -penter1  < /soft/car_ads_scrapper_training/db/DDL/create_objects.sql
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Creating database (mysql) users"
    echo
    sudo docker exec -i mysql mysql -uroot -penter1  < /soft/car_ads_scrapper_training/deployment/mysql_setup_users.sql
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Updating database (mysqld) settings"
    echo
    sudo docker exec -i mysql bash -c "cat > /etc/my.cnf" < /soft/car_ads_scrapper_training/deployment/mysql.cnf
#    if [ ! -f /var/lib/mysql/slow-query.log ]; then
#      mkdir touch /var/lib/mysql/slow-query.log && chown mysql:mysql /var/lib/mysql/slow-query.log
#    fi
#    if [ ! -f /var/lib/mysql/query.log ]; then
#      mkdir touch /var/lib/mysql/query.log && chown mysql:mysql /var/lib/mysql/query.log
#    fi
    echo
    echo

    # mysql --user=root --password="$(cat /root/.mysql)"

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Restaring rdbms (mysql) docker container"
    echo
    sudo docker restart mysql
    echo 
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Installing mysql client tool"
    echo
    sudo apt install --yes mysql-client
    echo
    echo

    # sudo useradd external-user
    # sudo passwd external-user
    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Sharing /mnt/disk-for-data/car_ads_scrapper_training network folder & setting up firewall"

    sudo apt install --yes nfs-kernel-server
    sudo systemctl enable nfs-server
    echo "/mnt/disk-for-data/car_ads_scrapper_training  spark-vm1(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
    echo "/mnt/disk-for-data/car_ads_scrapper_training  spark-vm2(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
    echo "/mnt/disk-for-data/car_ads_scrapper_training  scrapping-vm1(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
    echo "/mnt/disk-for-data/car_ads_scrapper_training  scrapping-vm2(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
    sudo ufw allow 111
    sudo ufw allow 2049
    sudo ufw allow 3306
    sudo exportfs -a
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Installing python dependencies"
    echo
    sudo apt install --yes python3-pip
    sudo pip3 install -r /soft/car_ads_scrapper_training/requirements_scrapper.txt
    echo
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Setting up db backup schedule"
    sudo cp /soft/car_ads_scrapper_training/deployment/mysql_daily_backup_script.sh /etc/cron.hourly/
    sudo chmod ugo+x /etc/cron.hourly/mysql_daily_backup_script.sh
    echo
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Waiting for everything to be started and mounted"
    echo
    echo
    # hope 1m is enough...
    sleep 30

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Create data-server-vm-configured file as a sign of the installation completed"
    echo
    cd /soft/car_ads_scrapper_training
    sudo touch /soft/car_ads_scrapper_training/data-server-vm-configured
    echo

    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "Starting your application"
    echo

    # sudo nohup python3 cards_scrapper_cars_com.py &
    # sudo python3 cards_finder_cars_com.py
    # sudo python3  streamingETL-cars-com-to-BQ.py
else
    echo "------------------------------------------------------------"
    echo $(date "+%Y-%m-%d %H:%M:%S") "The automation script had been executed previously"
    echo 
    echo
fi

echo "------------------------------------------------------------"
echo $(date "+%Y-%m-%d %H:%M:%S") "Waiting for everything to be started and mounted"
echo
echo

# hope 1m is enough...
sleep 30

#echo "------------------------------------------------------------"
#echo $(date "+%Y-%m-%d %H:%M:%S") "Starting your application"
#echo
#
#cd /soft/car_ads_scrapper_training
#
## sudo nohup python3 cards_scrapper_cars_com.py &
## sudo python3 cards_finder_cars_com.py
#
##sleep 30
#sudo python3  streamingETL-cars-com-to-BQ.py
#
#

