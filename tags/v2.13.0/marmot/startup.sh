#!/usr/bin/env bash

celeryWorkerNohup="./celeryworker_nohup.out"
celeryBeatNohup="./celerybeat_nohup.out"
uwsgiNohup="./uwsgi_nohup.out"

for f in $celeryWorkerNohup $celeryBeatNohup $uwsgiNohup; do
    if [ -a "$f" ]; then
        rm $f
    fi
done

nohup celery worker -A marmot -l info > celeryworker_nohup.out &
sleep 1
nohup celery beat -A marmot -l info > celerybeat_nohup.out &
sleep 1
nohup uwsgi marmot_uwsgi.ini > uwsgi_nohup.out &


# $ ps auxww | grep 'celery worker' | awk '{print $2}' | xargs kill -9
# $ ps auxww | grep 'uwsgi marmot' | awk '{print $2}' | xargs kill -9
