import random
import json

from engine import GameState

from queue import Queue
from paho.mqtt import client as mqttclient

q = Queue()

class GameEngine:

    def __init__(self):
        self.game_state = GameState()


    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'python-mqtt-{random.randint(0, 1000)}')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect('broker.emqx.io', 1883)
        return client

    def on_message(self, client, userdata, message):
        q.put(json.loads(message.payload.decode("utf-8")))

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)


    def run(self):

        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        mqttclient.subscribe("lasertag/vizhit")
        mqttclient.on_message = self.on_message

        while True:
            if not q.empty():
                # Get data from ext comms
                y = q.get()
                # ASSUME THAT EVAL_SERVER REPLIES HERE FROM EXT COMMS
                valid = self.game_state.update(y)
                print("received:" + json.dumps(y))
                if (valid): # only draw valid actions
                    action = y["action"]
                else:
                    action = "none"
                x = {
                    "type": "UPDATE",
                    "player_id": y["player_id"],
                    "action": action,
                    "isHit": y["isHit"],
                    "game_state": self.game_state.get_dict()
                }
                mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                print("sent UPDATE:" + json.dumps(x))

engine = GameEngine()
engine.run()
    



