# params: debug, noDupes (2p mode any player cannot go twice before the other), freePlay (no eval server)

import sys
import socket
import base64
import json
import asyncio

from engine import GameState
from predict import predict_action

from time import perf_counter
from random import randint, choice
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from multiprocessing import Process, Queue
from paho.mqtt import client as mqttclient

from pynq import Overlay

engine_to_eval_queue = Queue()
eval_to_engine_queue = Queue()

gun_thread_queue = Queue()
to_engine_queue = Queue()

relay_mlai_queues = [Queue() , Queue()]

debug = False
noDupes = False
freePlay = False
p1flag = False
p2flag = False
# BROKER = 'broker.emqx.io'
BROKER = '54.244.173.190'
# BROKER = '116.15.202.187'

DOUBLE_ACTION_WINDOW = 2.0
GUN_WINDOW = 1.0
SENSOR_WINDOW = 0.2


# This thread reads from the engine_to_eval_queue and sends all valid actions to the eval server.
class EvalClientThread:
    
    def __init__(self, ip_addr, port, secret_key):
        self.ip_addr        = ip_addr
        self.port           = port
        self.secret_key     = secret_key
  
        self.timeout        = 60
        self.is_running     = True

        game_state = GameState()
        self.x = {
            "player_id": "1",
            "action": "none",
            "game_state": game_state.get_dict()
        }
    
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
                        break
                    msg = data.decode("utf8")  # Decode raw bytes to UTF-8
                    success = True
                    break
            except asyncio.TimeoutError:
                timeout = -1
        else:
            timeout = -1

        global debug
        if debug:
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
        global debug

        await self.send_message("hello") 

        while True:
            msg = json.loads(engine_to_eval_queue.get()) # get valid actions from engine and send it to eval server

            x = {
                "player_id": msg["player_id"],
                "action": msg["action"],
                "game_state": msg["game_state"]
            }

            if debug:
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


# This thread receives data from the relay node via TCP and sends it to the gun/classification thread
class RelayCommsThread:
    
    def __init__(self, sn):
        self.timeout = 45
        self.is_running = True
        self.sn = sn
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', 10000 + self.sn)) # Binds to p1 relay on 10001, p2 relay on 10002


    async def receive_message(self, timeout):
        msg   = ""
        success = False

        if self.is_running:
            loop = asyncio.get_event_loop()
            try:
                while True:
                    data = b''
                    while not data.endswith(b'_'):
                        task = loop.sock_recv(self.conn, 1)
                        _d = await asyncio.wait_for(task, timeout=timeout)
                        if not _d:
                            data = b''
                            break
                        data += _d
                    if len(data) == 0:
                        break
                    data = data.decode("utf-8")
                    length = int(data[:-1])

                    data = b''
                    while len(data) < length:
                        task = loop.sock_recv(self.conn, length - len(data))
                        _d = await asyncio.wait_for(task, timeout=timeout)
                        if not _d:
                            data = b''
                            break
                        data += _d
                    if len(data) == 0:
                        break
                    msg = data.decode("utf8")  # Decode raw bytes to UTF-8
                    success = True
                    break
            except ConnectionResetError:
                print("relay " + str(self.sn) + " disconnected")
                self.conn, self.addr = await loop.sock_accept(self.sock)
                print("relay " + str(self.sn) + " connected")
            except asyncio.TimeoutError:
                timeout = -1
        else:
            timeout = -1

        return success, timeout, msg


    async def main(self):
        global debug

        while True:
            if not self.is_running:
                return
            self.sock.listen(1)
            self.sock.setblocking(False)

            loop = asyncio.get_event_loop()
            self.conn, self.addr = await loop.sock_accept(self.sock)
            print("relay " + str(self.sn) + " connected")
            while True:
                try:
                    task = self.receive_message(self.timeout)
                    success, timeout, text_received = await asyncio.wait_for(task, timeout=1500)

                    if text_received == '':
                        # invalid data
                        pass
                    elif text_received == 'KANA SHOT' or text_received == 'SHOTS FIRED':
                        if debug:
                            print("relay received: " + text_received + " , put on gun queue")
                        gun_thread_queue.put(str(self.sn) + text_received)
                    else:
                        if debug:
                            print("relay received: " + text_received + " , put on mlai queue")
                        relay_mlai_queues[self.sn - 1].put(text_received)

                except asyncio.TimeoutError:
                    print("relay " + str(self.sn) + " timeout")
                    self.conn, self.addr = await loop.sock_accept(self.sock)
                    print("relay " + str(self.sn) + " connected")


    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass
        

class GunLogicThread:

    def run(self):
        global debug

        p1gun = 0
        p2gun = 0
        p1vest = 0
        p2vest = 0
        p1gunflag = False
        p2gunflag = False
        timeout = None

        while True: 
            try:            
                msg = gun_thread_queue.get(timeout = timeout)
                currtime = perf_counter()

                if msg[1:] == 'KANA SHOT':
                    if msg[0] == '1':
                        if currtime < p2gun + GUN_WINDOW:
                            x = {
                                "player_id": '2',
                                "action": "gun",
                                "isHit": True
                            }
                            to_engine_queue.put(x)
                            p2gunflag = False
                            timeout = None
                        else:
                            p1vest = currtime
                            timeout = None
                    else:
                        if currtime < p1gun + GUN_WINDOW:
                            x = {
                                "player_id": '1',
                                "action": "gun",
                                "isHit": True
                            }
                            to_engine_queue.put(x)
                            p1gunflag = False
                            timeout = None
                        else:
                            p2vest = currtime
                            timeout = None

                elif msg[1:] == 'SHOTS FIRED':
                    if msg[0] == '1':
                        if currtime < p2vest + GUN_WINDOW:
                            x = {
                                "player_id": '1',
                                "action": "gun",
                                "isHit": True
                            }
                            to_engine_queue.put(x)
                            timeout = None
                        else:
                            p1gun = currtime
                            p1gunflag = True
                            # if p2 window is still active we set the timeout to its remaining time otherwise we set it to the default value for this shot
                            if p2gunflag:
                                timeout = p2gun + GUN_WINDOW - currtime
                            else:
                                timeout = GUN_WINDOW
                    else:
                        if currtime < p1vest + GUN_WINDOW:
                            x = {
                                "player_id": '2',
                                "action": "gun",
                                "isHit": True
                            }
                            to_engine_queue.put(x)
                            timeout = None
                        else:
                            p2gun = currtime
                            p2gunflag = True
                            # if p1 window is still active we set the timeout to its remaining time otherwise we set it to the default value for this shot
                            if p1gunflag:
                                timeout = p1gun + GUN_WINDOW - currtime
                            else:
                                timeout = GUN_WINDOW
                    
            except:
                currtime = perf_counter()
                if p1gunflag and currtime > p1gun + GUN_WINDOW:
                    x = {
                        "player_id": '1',
                        "action": "gun",
                        "isHit": False
                    }
                    to_engine_queue.put(x)
                    p1gunflag = False

                if p2gunflag and currtime > p2gun + GUN_WINDOW:
                    x = {
                        "player_id": '2',
                        "action": "gun",
                        "isHit": False
                    }
                    to_engine_queue.put(x)
                    p2gunflag = False

                timeout = None


# This thread will read from the relay_mlai_queue and identify the actions from sensor data, then publish it to the visualiser via MQTT. 
# For now it just forwards data to the visualizer via MQTT.
class ClassificationThread:

    def __init__(self, sn, ol):
        self.ol = ol
        self.sn = sn

    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'lasertagb01-class-{self.sn}')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect(BROKER, 1883)
        return client
    

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

            
    def run(self):
        global debug

        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        actions = ["portal", "web", "shield", "hammer", "grenade", "spear", "reload", "punch",  'logout', 'none']
        buffer = [0]*(30*8)
        pointer = 0
        lastaction = perf_counter()
        timeout = None
        toPublish = False

        while True:
            try:
                msg = relay_mlai_queues[self.sn - 1].get(timeout = timeout)

                if debug:
                    print("sensor reading get: " + msg)

                res = msg.strip("{}").split(",")

                for i in res:
                    buffer[pointer] = i
                    pointer += 1
                    # here we have received at least 30 packets
                    if pointer == 239:
                        if debug:
                            print("received " + str(pointer + 1) + "(full) packets, action to be identified")

                        action = actions[predict_action(buffer, 0, self.ol)]
                        toPublish = True
                        pointer = 0
                        timeout = None
                    else:
                        timeout = SENSOR_WINDOW

            except:
                # if we do not receive a packet in 200ms we assume that there has been packet drop and send it for classification.
                if pointer > 223:
                    if debug:
                        print("received " + str(pointer + 1) + " packets, action to be identified")

                    action = actions[predict_action(buffer, 0, self.ol)]
                    toPublish = True
                    pointer = 0
                # if too many packets are dropped we just discard it to be safe
                else:
                    if debug:
                        print("received " + str(pointer + 1) + " packets, data discarded")

                    toPublish = False
                    pointer = 0
                timeout = None

            if toPublish:
                # funky measure to stop actions that occur within 3s because they are likely to be misfires
                if perf_counter() > lastaction + DOUBLE_ACTION_WINDOW:
                    x = {
                        "type": "QUERY",
                        "player_id": self.sn,
                        "action": action,
                    }
                    mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                    lastaction = perf_counter()

                    if debug:
                        print(f"CLASSIFICATION{self.sn}: motion data passed to viz:" + json.dumps(x))
                else:
                    if debug:
                        print(f"CLASSIFICATION{self.sn}: WARNING! Double action discarded")
                
                buffer = [0]*(30*8)
                toPublish = False


# This is the game engine. It receives hit confirmations via MQTT and updates the game state accordingly. If it is a hit (valid action) it passes the
# action and game state to the eval_client for verification. It then puts the updated game state on the draw queue.
class GameEngine:

    def __init__(self):
        self.game_state = GameState()


    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'lasertagb01-engine')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect(BROKER, 1883)
        return client


    def on_message(self, client, userdata, message):
        to_engine_queue.put(json.loads(message.payload.decode("utf-8")))
        

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)


    def run(self):
        global debug

        global p1flag
        global p2flag

        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        mqttclient.subscribe("lasertag/vizhit")
        mqttclient.on_message = self.on_message

        custom_actions = ["none"]

        while True:
            msg = to_engine_queue.get()

            if debug:
                print("Engine update:" + str(msg))

            # if we check for dupes we do not accept dupes from the same player
            if noDupes:
                player_id = msg["player_id"]
                if player_id == "1" and p1flag == True:
                    continue
                if player_id == "2" and p2flag == True:
                    continue

                # never allow a player to send 2 consecutive actions in the same round (2 player)
                if player_id == "1":
                    if p2flag == True:
                        p2flag = False
                    else:
                        p1flag = True
                else:
                    if p1flag == True:
                        p1flag = False
                    else:
                        p2flag = True

            # update gamestate
            valid = self.game_state.update(msg) 

            x = {
                "player_id": msg["player_id"],
                "action": msg["action"],
                "game_state": self.game_state.get_dict()
            }
            
            # we dont send our actions to eval server in freeplay, or custom actions to the eval server at all
            if not freePlay and msg["action"] not in custom_actions:
                engine_to_eval_queue.put(json.dumps(x))

                # NOTE: THIS IS BLOCKING because we need verification from eval server, and we want to avoid desync
                eval_server_game_state = json.loads(eval_to_engine_queue.get())

                # overwrite our game state with the eval server's if ours is wrong
                if eval_server_game_state != self.game_state.get_dict(): 
                    print("WARNING: EVAL SERVER AND ENGINE DESYNC, RESYNCING")
                    self.game_state.overwrite(eval_server_game_state)

            if valid: # only draw valid actions
                action = msg["action"]
            else:
                action = "none"

            # put updated game state on queue for drawing
            x = {
                "type": "UPDATE",
                "player_id": msg["player_id"],
                "action": action,
                "isHit": msg["isHit"],
                "game_state": self.game_state.get_dict()
            }

            if debug:
                print("final update forwarded to viz:" + json.dumps(x))
            mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                    

if sys.argv[1] == "1":
    debug = True

if sys.argv[2] == "1":
    noDupes = True

if sys.argv[3] == "1":
    freePlay = True

if not freePlay:
    # actual server
    # host = "172.25.76.133"
    host = "127.0.0.1"
    secret_key = bytes(str('1111111111111111'), encoding="utf8")  # Convert password to bytes

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

    eval_client = EvalClientThread(host, port, secret_key)
    evalclient = Process(target=eval_client.run)
    evalclient.start()

ol = Overlay("action.bit")

relaycomms_client1 = RelayCommsThread(1)
relaycomms_client2 = RelayCommsThread(2)
classification_thread1 = ClassificationThread(1, ol)
classification_thread2 = ClassificationThread(2, ol)
gun_thread = GunLogicThread()
game_engine = GameEngine()

relay1 = Process(target=relaycomms_client1.run)
relay2 = Process(target=relaycomms_client2.run)
classification1 = Process(target=classification_thread1.run)
classification2 = Process(target=classification_thread2.run)
gun = Process(target=gun_thread.run)
engine = Process(target=game_engine.run)

relay1.start()
relay2.start()
gun.start()
engine.start()
classification1.start()
classification2.start()

relay1.join()
relay2.join()
gun.join()
engine.join()
classification1.join()
classification2.join()

if not freePlay:
    evalclient.join()
