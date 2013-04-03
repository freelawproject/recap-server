#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y install python-software-properties
add-apt-repository -y ppa:fkrull/deadsnakes && apt-get update
apt-get -y install curl patch mysql-server python-pip libxslt1-dev libxml2-dev libmysqlclient-dev libssl-dev python2.5 python2.5-dev screen

# There is a strange bug in MySQL
echo "FLUSH PRIVILEGES; DROP USER 'recapper'; FLUSH PRIVILEGES;" | mysql -uroot
echo "CREATE USER 'recapper'@'localhost' IDENTIFIED BY 'recap';
CREATE DATABASE IF NOT EXISTS recap_dev;
GRANT ALL PRIVILEGES ON recap_dev . * TO 'recapper'@'localhost';" | mysql -uroot

# Install virtualenv and create a 2.5 RECAP virtualenv
pip install virtualenvwrapper
export WORKON_HOME=~/Envs
mkdir -p $WORKON_HOME
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -p $(which python2.5) RECAP

ln -s /vagrant recap-server
cd recap-server
pip install --insecure -r requirements.txt

export PYTHONPATH=/home/vagrant
python manage.py syncdb
screen -d -m -S RECAP sh -c 'python manage.py runserver 0.0.0.0:8000; exec bash'
