import sys
import socket
import base64
import json
import asyncio
import random
import threading

from engine import GameState

from time import perf_counter
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from queue import Queue
from paho.mqtt import client as mqttclient


engine_to_eval_queue = Queue()
eval_to_engine_queue = Queue()

mqtt_vizhit_queue = Queue()
relay_mlai_queue = Queue()

draw_queue = Queue()

debug = False

# This thread reads from the engine_to_eval_queue and sends all valid actions to the eval server.
class EvalClientThread:
    
    def __init__(self, ip_addr, port, secret_key):
        self.ip_addr        = ip_addr
        self.port           = port
        self.secret_key     = secret_key
  
        self.timeout        = 60
        self.is_running     = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip_addr, self.port))
        # Login
    

    async def send_message(self, msg):
        msg = pad(bytes(msg, encoding="utf-8"), AES.block_size)
        iv = Random.new().read(AES.block_size)  # Get IV value
        cipher = AES.new(self.secret_key, AES.MODE_CBC, iv)  # Create new AES cipher object
        
        encoded_message = base64.b64encode(iv + cipher.encrypt(msg))  # Encode message from bytes to base64
    
        self.sock.sendall(bytes((str(len(encoded_message)) + '_'), encoding="utf-8"))
        self.sock.sendall(encoded_message)


    async def receive_message(self, timeout):
        msg   = ""
        success = False

        if self.is_running:
            loop = asyncio.get_event_loop()
            try:
                while True:
                    # recv length followed by '_' followed by cypher
                    data = b''
                    while not data.endswith(b'_'):
                        start_time = perf_counter()
                        task = loop.sock_recv(self.sock, 1)
                        _d = await asyncio.wait_for(task, timeout=timeout)
                        timeout -= (perf_counter() - start_time)
                        if not _d:
                            data = b''
                            break
                        data += _d
                    if len(data) == 0:
                        self.stop()
                        break
                    data = data.decode("utf-8")
                    length = int(data[:-1])

                    data = b''
                    while len(data) < length:
                        start_time = perf_counter()
                        task = loop.sock_recv(self.sock, length - len(data))
                        _d = await asyncio.wait_for(task, timeout=timeout)
                        timeout -= (perf_counter() - start_time)
                        if not _d:
                            data = b''
                            break
                        data += _d
                    if len(data) == 0:
                        self.stop()
                        break
                    msg = data.decode("utf8")  # Decode raw bytes to UTF-8
                    success = True
                    break
            except ConnectionResetError:
                self.stop()
            except asyncio.TimeoutError:
                timeout = -1
        else:
            timeout = -1

        global debug
        if debug is True:
            print("Evalclient received: " + msg)

        return success, timeout, msg


    def decrypt_message(self, cipher_text):
        """
        This function decrypts the response message received from the Ultra96 using
        the secret encryption key/ password
        """
        try:
            decoded_message = base64.b64decode(cipher_text)  # Decode message from base64 to bytes
            iv = decoded_message[:AES.block_size]  # Get IV value
            secret_key = bytes(str(self.secret_key), encoding="utf8")  # Convert secret key to bytes

            cipher = AES.new(secret_key, AES.MODE_CBC, iv)  # Create new AES cipher object

            decrypted_message = cipher.decrypt(decoded_message[AES.block_size:])  # Perform decryption
            decrypted_message = unpad(decrypted_message, AES.block_size)
            decrypted_message = decrypted_message.decode('utf8')  # Decode bytes into utf-8
        except Exception as e:
            decrypted_message = ""
        return decrypted_message


    async def main(self):

        await self.send_message("hello") 

        while True:
            if not engine_to_eval_queue.empty():
                msg = json.loads(engine_to_eval_queue.get()) # get valid actions from engine and send it to eval server

                x = {
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "game_state": msg["game_state"]
                }

                global debug
                if debug is True:
                    print("sending json to eval server:" + json.dumps(x))

                await self.send_message(json.dumps(x))

                success, timeout, text_received = await self.receive_message(self.timeout)

                if success:
                    eval_to_engine_queue.put(text_received)
                else:
                    print("WARNING! NO REPLY RECEIVED FROM EVAL_SERVER")


    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass


# This thread (1 for each player) connects to relay via TCP and passes received data to the classification (MLAI) thread. 
class RelayCommsThread:

    def __init__(self, sn):
        self.sn = sn
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', 10000 + self.sn)) # Binds to p1 relay on 10001, p2 relay on 10002


    def send_message(self, msg):
        encoded_message = base64.b64encode(msg)  # Encode message from bytes to base64

        self.sock.sendall(bytes((str(len(encoded_message)) + '_'), encoding="utf-8"))
        self.sock.sendall(encoded_message)


    def handle_relay(self, conn):
        while True:
            msg = conn.recv(1024).decode("utf-8") # TODO: Change recv(1024)
            global debug
            if debug is True:
                print("motion received put on queue: " + msg)
            relay_mlai_queue.put(json.loads(msg)) # Identify action

    
    def run(self):

        self.sock.listen()
        global debug
        if debug is True:
            print("relay-ultra96 thread " + str(self.sn) + " listening")

        while True:
            (conn, address) = self.sock.accept()
            self.handle_relay(conn)


# This thread will from the relay_mlai_queue and identify the actions from sensor data, then publish it to the visualiser via MQTT. 
# For now it just forwards data to the visualizer via MQTT.
class ClassificationThread:

    def __init__(self, sn):
        self.sn = sn
 

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

        mqttclient.subscribe("lasertag/vizgamestate")

        while True:
            if not relay_mlai_queue.empty():
                msg = relay_mlai_queue.get()
                # identify action
                x = {
                    "type": "QUERY",
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                }
                global debug
                if debug is True:
                    print("motion data forwarded to viz:" + json.dumps(x))
                mqttclient.publish("lasertag/vizgamestate", json.dumps(x))


# This thread reads from the draw_queue, and publishes via MQTT for the visualiser to draw.
class VisualiserUpdateThread:

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

        mqttclient.subscribe("lasertag/vizgamestate")

        while True:
            if not draw_queue.empty():
                msg = json.loads(draw_queue.get())
                x = {
                    "type": "UPDATE",
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "game_state": msg["game_state"]
                }
                global debug
                if debug is True:
                    print("final update forwarded to viz:" + json.dumps(x))
                mqttclient.publish("lasertag/vizgamestate", json.dumps(x))


# This is the game engine. It receives hit confirmations via MQTT and updates the game state accordingly. If it is a hit (valid action) it passes the
# action and game state to the eval_client for verification. It then puts the updated game state on the draw queue.
class GameEngine:

    def __init__(self) -> None:
        self.game_state = GameState()


    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'python-mqtt-{random.randint(0, 1000)}')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect('broker.emqx.io', 1883)
        return client


    def on_message(self, client, userdata, message):
        mqtt_vizhit_queue.put(json.loads(message.payload.decode("utf-8")))
        

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
            if not mqtt_vizhit_queue.empty():
                # get actions from vizhit
                msg = mqtt_vizhit_queue.get()

                global debug
                if debug is True:
                    print("Engine update:" + str(msg))

                # update gamestate
                self.game_state.update(msg) 

                x = {
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "game_state": self.game_state.get_dict()
                }
                        
                # we only send valid actions (hits) to the eval_server
                if (msg["isHit"] == True):
                    engine_to_eval_queue.put(json.dumps(x))

                    # NOTE: THIS IS BLOCKING because we need verification from eval server, and we want to avoid desync
                    eval_server_game_state = json.loads(eval_to_engine_queue.get()) 
                    
                    # overwrite our game state with the eval server's if ours is wrong
                    if (eval_server_game_state != self.game_state.get_dict()): 
                        print("WARNING: EVAL SERVER AND ENGINE DESYNC, RESYNCING")
                        self.game_state.overwrite(eval_server_game_state)

                # put updated game state on queue for drawing
                x = {
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "isHit": msg["isHit"],
                    "game_state": self.game_state.get_dict()
                }
                draw_queue.put(json.dumps(x))
                    

# actual server
# host = "172.25.76.133"
 
host = "127.0.0.1"


while True:
    try:
        port = int(input("Enter port:"))
        break

    except ValueError:
        print("Port has to be an integer.")
        continue

    except OverflowError:
        print("Port has to be between 0 and 65535.")
        continue

    except ConnectionRefusedError:
        print("Connection refused.")
        continue


if sys.argv[1] == "1":
    debug = True

secret_key = bytes(str('1111111111111111'), encoding="utf8")  # Convert password to bytes

eval_client = EvalClientThread(host, port, secret_key)
relaycomms_client1 = RelayCommsThread(1)
relaycomms_client2 = RelayCommsThread(2)
classification_thread = ClassificationThread()
game_engine = GameEngine()
viz_draw = VisualiserUpdateThread()

evalclient = threading.Thread(target=eval_client.run)
relay1 = threading.Thread(target=relaycomms_client1.run)
relay2 = threading.Thread(target=relaycomms_client2.run)
classification = threading.Thread(target=classification_thread.run)
engine = threading.Thread(target=game_engine.run)
draw = threading.Thread(target=viz_draw.run)

evalclient.start()
relay1.start()
relay2.start()
classification.start()
engine.start()
draw.start()

evalclient.join()
relay1.join()
relay2.join()
classification.join()
engine.join()
draw.join



