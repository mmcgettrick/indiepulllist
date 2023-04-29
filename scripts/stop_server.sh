#! /bin/bash
# Shutdown gunicorn if it's running...
PIDFILE=/home/ec2-user/gunicorn.pid
if [ -f "$PIDFILE" ]; then
    kill -9 `cat $PIDFILE`
    rm $PIDFILE
fi
