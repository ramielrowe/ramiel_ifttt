import os

import flask
from flask import request
import requests
import rxv
from zeroconf import ServiceBrowser, Zeroconf

FLASK_PORT = os.environ.get('FLASK_PORT', 8080)
IFTTT_SECRET = os.environ.get('IFTTT_SECRET')

RECEIVER_URL = "http://{}:80/YamahaRemoteControl/ctrl"

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
    
    address = body['address']
    on = body.get('on')
    input = body.get('input')
    
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

    return ""

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(FLASK_PORT))
    cast_listener.close()
    print('done')
