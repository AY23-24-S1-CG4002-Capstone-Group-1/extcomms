import asyncio
import random
import json

from queue import Queue
from paho.mqtt import client as mqttclient

q = Queue()

# PLACEHOLDER, VIZ MQTT CLIENT WILL BE IN UNITY


def connect_mqtt():
    # Set Connecting Client ID
    client = mqttclient.Client(f'python-mqtt-{random.randint(0, 1000)}')
    client.on_connect = on_connect
    # client.username_pw_set(username, password)
    client.connect('broker.emqx.io', 1883)
    return client


def on_message(client, userdata, message):
    q.put(json.loads(message.payload.decode("utf-8")))
    

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


async def main():
    mqttclient = connect_mqtt()
    mqttclient.loop_start()

    mqttclient.subscribe("lasertag/vizgamestate")
    mqttclient.on_message = on_message

    while True:
        if not q.empty():
            msg = q.get()
            print("Viz received data:" + str(msg))
            x = {
                "player_id": msg["player_id"],
                "action": msg["action"],
                "hit" : True
            }
            mqttclient.publish("lasertag/vizhit", json.dumps(x))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


    



