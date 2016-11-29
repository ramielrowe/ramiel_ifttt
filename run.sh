#!/bin/bash

. env.sh

docker build -t ramiel_ifttt .

docker stop -t 5 ramiel_ifttt
docker rm -fv ramiel_ifttt

docker run -d --name ramiel_ifttt \
    --restart always \
    --net host \
    -e IFTTT_SECRET=${IFTTT_SECRET} \
    -e FLASK_PORT=${FLASK_PORT} \
    ramiel_ifttt
