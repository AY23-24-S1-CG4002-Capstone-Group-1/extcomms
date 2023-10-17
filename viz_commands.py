import random
import json

from paho.mqtt import client as mqttclient

class MQTTClient:

    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'python-mqtt-{random.randint(0, 1000)}')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect('broker.emqx.io', 1883)
        # client.connect('127.0.0.1', 1883)
        # client.connect('116.15.202.85', 1883)
        return client


    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)


    def run(self):
        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()
    
        while True:
            command = input("Enter command: ")

            try:
                x = command.split()
                player_id = x[0]
                action = x[1]
                x = {
                    "type": "QUERY",
                    "player_id": player_id,
                    "action": action,
                }
                mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                print("sent QUERY:" + json.dumps(x))

            except:
                print("error, enter player_id and action eg: 1 gun")
                pass

client = MQTTClient()
client.run()