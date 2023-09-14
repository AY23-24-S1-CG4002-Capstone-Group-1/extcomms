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

mqtt_vizhit_queue = Queue()
mqtt_motion_queue = Queue()

debug = False


game_state = GameState()


class EvalClient:
    
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
                msg = json.loads(engine_to_eval_queue.get())
                print(msg["game_state"])
                x = {
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "game_state": msg["game_state"]
                }
                global debug
                if debug is True:
                    print("sending json:" + json.dumps(x))
                await self.send_message(json.dumps(x))
                success, timeout, text_received = await self.receive_message(self.timeout)
                if success:
                    data = json.loads(text_received)


    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass


class RelayCommsClient:

    def __init__(self, sn):
        self.sn = sn
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', 10000 + self.sn))


    def send_message(self, msg):
        encoded_message = base64.b64encode(msg)  # Encode message from bytes to base64

        self.sock.sendall(bytes((str(len(encoded_message)) + '_'), encoding="utf-8"))
        self.sock.sendall(encoded_message)


    def handle_relay(self, conn):
        while True:
            msg = conn.recv(1024).decode("utf-8")
            global debug
            if debug is True:
                print("motion received put on queue: " + msg)
            mqtt_motion_queue.put(json.loads(msg))

    
    def run(self):

        self.sock.listen()
        global debug
        if debug is True:
            print("relay-ultra96 thread " + str(self.sn) + " listening")

        while True:
            (conn, address) = self.sock.accept()
            # now do something with the clientsocket
            # in this case, we'll pretend this is a threaded server
            self.handle_relay(conn)


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
            if not mqtt_motion_queue.empty():
                msg = mqtt_motion_queue.get()
                # identify action
                global game_state
                x = {
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "game_state": game_state.get_dict()
                }
                global debug
                if debug is True:
                    print("motion data forwarded to viz:" + json.dumps(x))
                mqttclient.publish("lasertag/vizgamestate", json.dumps(x))


class GameEngine:

    def __init__(self) -> None:
        global game_state
        self.game_state = game_state


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
                # these are valid actions (actions that land because opposing player is within viz)
                msg = mqtt_vizhit_queue.get()

                global debug
                if debug is True:
                    print("Engine update:" + str(msg))

                # update gamestate
                self.game_state.update(msg)
                global game_state
                game_state = self.game_state
                        
                x = {
                    "player_id": msg["player_id"],
                    "action": msg["action"],
                    "game_state": self.game_state.get_dict()
                }
                engine_to_eval_queue.put(json.dumps(x))

# home
# host = "192.168.56.1"

# nus-stu
# host = "192.168.137.1"
 
# actual server
host = "172.25.76.133"
 
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

eval_client = EvalClient(host, port, secret_key)
relaycomms_client1 = RelayCommsClient(1)
classification_thread1 = ClassificationThread(1)
relaycomms_client2 = RelayCommsClient(2)
classification_thread2 = ClassificationThread(2)
game_engine = GameEngine()

evalclient = threading.Thread(target=eval_client.run)
relay1 = threading.Thread(target=relaycomms_client1.run)
class1 = threading.Thread(target=classification_thread1.run)
relay2 = threading.Thread(target=relaycomms_client2.run)
class2 = threading.Thread(target=classification_thread2.run)
engine = threading.Thread(target=game_engine.run)

evalclient.start()
relay1.start()
class1.start()
relay2.start()
class2.start()
engine.start()

evalclient.join()
relay1.join()
class1.join()
relay2.join()
class2.join()
engine.join()



