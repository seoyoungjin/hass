#! /usr/bin/python3

import socket
import binascii
import struct
import json
import paho.mqtt.client as mqtt
import syslog
 
 
MQTT_SERVER = "localhost"
MQTT_PORT = 1883
 
PATH_FMT = "xiaomi/{model}/{sid}/{prop}" # short_id or sid ?
 
def prepare_mqtt():
    client = mqtt.Client()
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
 
    return client
 
def push_data(client, model, sid, cmd, data):
    for key, value in data.items():
        path = PATH_FMT.format(model=model,
                               sid=sid,
                               cmd=cmd,
                               prop=key)
        syslog.syslog(syslog.LOG_INFO, "PUSH path=(%s), payload=(%s)" % (path, value))
        client.publish(path, payload=value, qos=0)
 
class XiaomiConnector:
    MULTICAST_PORT = 9898
    SERVER_PORT = 4321
 
    MULTICAST_ADDRESS = '224.0.0.50'
    SOCKET_BUFSIZE = 1024
 
    def __init__(self, data_callback=None, auto_discover=True):
        self.data_callback = data_callback
        self.last_tokens = dict()
        self.socket = self._prepare_socket()
 
        self.nodes = dict()
    
    def _prepare_socket(self):
        sock = socket.socket(socket.AF_INET, # Internet
                             socket.SOCK_DGRAM) # UDP
 
        sock.bind(("0.0.0.0", self.MULTICAST_PORT))
 
        mreq = struct.pack("=4sl", socket.inet_aton(self.MULTICAST_ADDRESS),
                           socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                        self.SOCKET_BUFSIZE)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
 
        return sock
 
    def check_incoming(self):
        print("checking")
        data, addr = self.socket.recvfrom(self.SOCKET_BUFSIZE)
        try:
            payload = json.loads(data.decode("utf-8"))
            print(payload)
            self.handle_incoming_data(payload)
 
        except Exception as e:
            raise
            syslog.syslog(syslog.LOG_ERROR, "Can't handle message %r (%r)" % (data, e))
 
    def handle_incoming_data(self, payload):
        if isinstance(payload.get('data', None), str):
            cmd = payload["cmd"]
            if cmd in ["heartbeat", "report", "read_ack"]:
                if self.data_callback is not None:
                    self.data_callback(payload["model"],
                                       payload["sid"],
                                       payload["cmd"],
                                       json.loads(payload["data"]))
 
            if cmd == "read_ack" and payload["sid"] not in self.nodes:
                self.nodes[payload["sid"]] = dict(model=payload["model"])
 
            if cmd == "heartbeat" and payload["sid"] not in self.nodes:
                self.request_sids(payload["sid"])
                self.nodes[payload["sid"]] = json.loads(payload["data"])
                self.nodes[payload["sid"]]["model"] = payload["model"]
                self.nodes[payload["sid"]]["sensors"] = []
 
            if cmd == "get_id_list_ack":
                device_sids = json.loads(payload["data"])
                self.nodes[payload["sid"]]["nodes"] = device_sids
 
                for sid in device_sids:
                    self.request_current_status(sid)
 
        if "token" in payload:
            self.last_tokens[payload["sid"]] = payload['token']
 
    def request_sids(self, sid):
        self.send_command({"cmd":"get_id_list", sid: sid})
 
    def request_current_status(self, device_sid):
        self.send_command({"cmd":"read", "sid": device_sid})
 
    def send_command(self, data):
        self.socket.sendto(json.dumps(data).encode("utf-8"),
                           (self.MULTICAST_ADDRESS, self.MULTICAST_PORT))
 
    def get_nodes(self):
        return self.nodes
    
if __name__ == "__main__":
    syslog.openlog(ident="Aqara")
    client = prepare_mqtt()
    cb = lambda m, s, c, d: push_data(client, m, s, c, d)
    connector = XiaomiConnector(data_callback=cb)
 
    while True:
        connector.check_incoming()
