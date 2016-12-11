from concurrent import futures
import os
import queue

from braviarc import braviarc
import flask
from flask import request
import requests
import rxv
from zeroconf import ServiceBrowser, Zeroconf

FLASK_PORT = os.environ.get('FLASK_PORT', 8080)
IFTTT_SECRET = os.environ.get('IFTTT_SECRET')

RECEIVER_URL = "http://{}:80/YamahaRemoteControl/ctrl"

TASK_QUEUE = queue.Queue()


class ChromecastListener(object):
    def __init__(self):
        self.zconf = Zeroconf()
        self.browser = ServiceBrowser(self.zconf, "_googlecast._tcp.local.", self)
        self.casts = {}

    def remove_service(self, zeroconf, type, name):
        if name in self.casts:
            del self.casts[name]

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ips = zeroconf.cache.entries_with_name(info.server.lower())
        host = repr(ips[0]) if ips else info.server
        friendly_name = info.properties.get('fn'.encode('utf-8')).decode('utf-8')
        self.casts[name] = {'friendly_name': friendly_name,
                            'host': host, 'port': info.port}

    def close(self):
        self.zconf.close()

    def get_cast(self, friendly_name):
        for cast in self.casts.values():
            if cast['friendly_name'] == friendly_name:
                return cast


cast_listener = ChromecastListener()
app = flask.Flask(__name__)


@app.route("/chromecast/youtube", methods=['POST'])
def chromecast_youtube_endpoint():
    body = request.get_json()
    if IFTTT_SECRET and body.get('secret') != IFTTT_SECRET:
        return ""
    name = body['chromecast']
    video = body['video']
    cast = cast_listener.get_cast(name)
    if not cast:
        return ""
    requests.post('http://{}:{}/apps/YouTube'.format(cast['host'], 8008),
                  data="v={}".format(video))
    return ""


@app.route("/receiver", methods=['POST'])
def receiver_endpoint():
    body = request.get_json()
    if IFTTT_SECRET and body.get('secret') != IFTTT_SECRET:
        return ""
    TASK_QUEUE.put(('receiver', body))
    return ""


def _receiver_endpoint(body):
    address = body['address']
    on = body.get('on')
    input = body.get('input')
    volume = body.get('volume')
    
    receiver = rxv.RXV(RECEIVER_URL.format(address))

    try:
        if not receiver.basic_status:
            return ""
    except Exception as e:
        return ""

    if on is not None:
        receiver.on = on

    if on and input:
        receiver.input = input

    if volume and volume[0] == '+':
        receiver.volume = receiver.volume + int(volume[1:])
    elif volume and volume[0] == '-':
        receiver.volume = receiver.volume - int(volume[1:])
    elif volume:
        receiver.volume = int(volume)

    return ""


@app.route("/tv", methods=['POST'])
def tv_endpoint():
    body = request.get_json()
    if IFTTT_SECRET and body.get('secret') != IFTTT_SECRET:
        return ""
    TASK_QUEUE.put(('tv', body))
    return ""


def _tv_endpoint(body):
    address = body['address']
    pin = body['pin']
    on = body.get('on')
    cmd = body.get('cmd')

    brc = braviarc.BraviaRC(address)
    brc.connect(pin, 'ramiel_ifttt', 'ramiel_ifttt')

    if on is not None:
        if on:
            brc.turn_on()
        else:
            brc.turn_off()

    if cmd == 'play':
        brc.media_play()
    elif cmd == 'pause':
        brc.media_pause()

    return ""


def dict_hash(d):
    return hash(frozenset(d.items()))


def handle_task(task, body):
    print("{}: {}".format(task, body))
    if task == 'receiver':
        _receiver_endpoint(body)
    elif task == 'tv':
        _tv_endpoint(body)


def queue_worker():
    next_task, next_body = None, None
    while True:
        task, body = TASK_QUEUE.get()
        handle_task(task, body)
        try:
            deduping = True
            timeout = 3
            while deduping:
                deduping = False
                next_task, next_body = TASK_QUEUE.get(timeout=timeout)
                if next_task == task and body == next_body:
                    deduping = True
                    next_task, next_body = None, None
                    timeout = 1
        except queue.Empty:
            pass

        if next_task:
            handle_task(next_task, next_body)
            next_task, next_body = None, None


if __name__ == "__main__":
    with futures.ThreadPoolExecutor(max_workers=1) as exc:
        exc.submit(queue_worker)
        app.run(host='0.0.0.0', port=int(FLASK_PORT))
    cast_listener.close()
    print('done')
