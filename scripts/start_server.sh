#! /bin/bash
cd /home/ec2-user/ipl
source /home/ec2-user/environment.sh
/usr/local/bin/gunicorn -w 4 application --log-file /home/ec2-user/gunicorn.log --log-level=warning -p /home/ec2-user/gunicorn.pid -D
