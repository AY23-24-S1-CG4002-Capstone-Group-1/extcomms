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


    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)


    def run(self):

        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        mqttclient.subscribe("lasertag/vizhit")

        while True:
            command = input("Enter command: ")

            if command == "reset":
                self.game_state = GameState()
                break
            else:
                try:
                    x = command.split()
                    player_id = x[0]
                    action = x[1]
                    y = {
                        "player_id": player_id,
                        "action": action,
                        "isHit": True
                    }
                    self.game_state.update(y)
                    x = {
                        "type": "UPDATE",
                        "player_id": player_id,
                        "action": action,
                        "game_state": self.game_state.get_dict()
                    }
                    mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                    print("sent:" + json.dumps(x))

                except:
                    print("error, enter player_id and action eg: 1 gun")
                    pass



gameengine = GameEngine()
gameengine.run()


    



