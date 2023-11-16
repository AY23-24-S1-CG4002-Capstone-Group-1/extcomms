import asyncio
from queue import Queue
from time import perf_counter, sleep
from statistics import median, mean
from paho.mqtt import client as mqttclient

# BROKER = '116.15.202.187'
# BROKER = 'broker.emqx.io'
BROKER = 'test.mosquitto.org'
# BROKER = 'broker.hivemq.com'    


class MqttTestClient:
    
    def __init__(self):
        self.mqtt_queue = Queue()

    def connect_mqtt(self):
        client = mqttclient.Client(f'lasertagtest')
        client.on_connect = self.on_connect
        client.connect(BROKER, 1883)
        return client  

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_message(self, client, userdata, message):
        self.mqtt_queue.put("msg received")

    async def send_message(self, msg):
        self.sock.sendall(bytes((str(len(msg)) + '_'), encoding="utf-8"))
        self.sock.sendall(bytes(msg, encoding="utf-8"))

    async def main(self):

        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        mqttclient.subscribe("cg4002speedtest")
        mqttclient.on_message = self.on_message
        arr = []

        for i in range(200):
            sleep(0.5)
            x = "test"
            mqttclient.publish("cg4002speedtest", x)
            start = perf_counter()
            self.mqtt_queue.get()
            timetaken = perf_counter() - start
            arr.append(timetaken)
            print(timetaken)

        print("Mean: " + str(mean(arr)))
        print("Median " + str(median(arr)))
        print("High: " + str(max(arr)))
        print("Low: " + str(min(arr)))
                

    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass


testClient = MqttTestClient()
testClient.run()


