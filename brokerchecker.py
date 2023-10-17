import socket
import json
import asyncio
from random import randint
from queue import Queue
from paho.mqtt import client as mqttclient
import threading

# BROKER = 'broker.emqx.io'
BROKER = "116.15.202.187"

relay_queue = Queue()
mqtt_queue = Queue()

class MQTTClient:

    def __init__(self, sn):
        self.sn = int(sn)

    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'lasertagb01-viztestrelay{self.sn}')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect(BROKER, 1883)
        return client
    

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)


    def on_message(self, client, userdata, message):
        mqtt_queue.put(json.loads(message.payload.decode("utf-8")))

            
    def run(self):
        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        mqttclient.subscribe("lasertag/vizgamestate")
        mqttclient.on_message = self.on_message

        while True:
            if not mqtt_queue.empty():
                msg = mqtt_queue.get()
                if msg['type'] == "UPDATE":
                    if self.sn == 1:
                        hp = msg['game_state']['p1']['hp']
                        bullets = msg['game_state']['p1']['bullets']
                    else:
                        hp = msg['game_state']['p2']['hp']
                        bullets = msg['game_state']['p2']['bullets']
                
                    print("hp: " + str(hp) + "bullets: " + str(bullets))


sn = input("Enter player number:")

mqtt_client = MQTTClient(sn)
mqtt_client.run()


