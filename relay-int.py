import socket
import json
import asyncio
from random import randint
from queue import Queue
from paho.mqtt import client as mqttclient
import threading

BROKER = '116.15.202.187'
# BROKER = 'broker.emqx.io'
# BROKER = 'test.mosquitto.org'

relay_queue = Queue()
mqtt_queue = Queue()


'''
Mock relay client that simulates send data. Commands:
action: Sends 32 packets to generate random action
drop:  Sends 26 packets. Should be discarded by ultra96
double: Sends 60 packets. Random action generated, second discarded
gun: Fires gun
vest: Fires vest
both: Fires both

Also has a mqtt subscriber that will print the updated game state from the ultra96.
'''


class RelayClient:
    
    def __init__(self, sn):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sn = int(sn)


    async def send_message(self, msg):
        self.sock.sendall(bytes((str(len(msg)) + '_'), encoding="utf-8"))
        self.sock.sendall(bytes(msg, encoding="utf-8"))

    
    async def main(self):
        self.sock.connect(('172.26.190.113', 10000 + self.sn)) 

        print("connected")

        while True:
            command = input("Enter command: ")

            if command == "q":
                break
            else:
                if command == "action":
                    for i in range(32):
                        msg = "{" + str(randint(0, 256)) + ","  + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) \
                        + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "}"
                        print(msg)
                        await self.send_message(msg)
                if command == "drop":
                    for i in range(26):
                        msg = "{" + str(randint(0, 256)) + ","  + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) \
                        + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "}"
                        await self.send_message(msg)
                if command == "double":
                    for i in range(60):
                        msg = "{" + str(randint(0, 256)) + ","  + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) \
                        + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "," + str(randint(0, 256)) + "}"
                        await self.send_message(msg)
                if command == "both":
                    await self.send_message("KANA SHOT")
                    await self.send_message("SHOTS FIRED")
                if command == "gun":
                    await self.send_message("SHOTS FIRED")
                if command == "vest":
                    await self.send_message("KANA SHOT")

    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass


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

relay_client = RelayClient(sn)
relay_thread = threading.Thread(target=relay_client.run)
relay_thread.start()

mqtt_client = MQTTClient(sn)
mqtt_thread = threading.Thread(target=mqtt_client.run)
mqtt_thread.start()

# ic_thread.join()
# relay_thread.join()
# mqtt_thread.join()


