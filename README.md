ramiel\_ifttt
=============

Simple flask app to expose automation tasks via HTTP calls.

It supports:
* Playing Youtube videos on a Chromecast device.

Running
=======

You can run it locally by running the following commands.

    $ virtualenv -p $(which python3) .venv
    $ source .venv/bin/active
    $ pip3 install -r requirements
    $ FLASK_PORT=8080 python3 app.py

You can run it via docker by running the following commands.

    $ docker build -t ramiel_ifttt .
    $ docker run -d --name ramiel_ifttt --net host \
             -e FLASK_PORT=8080 \
             -e IFTTT_SECRET=some_super_secret \
             ramiel_ifttt

Note that when running with Docker, the container needs to be
on the hosts network, otherwise Chromecast discovery won't work.
