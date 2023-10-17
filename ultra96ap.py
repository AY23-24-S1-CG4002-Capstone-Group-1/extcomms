import sys
import socket
import base64
import json
import asyncio

from engine import GameState
from predict import predict_action

from time import perf_counter
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from multiprocessing import Process, Queue
from paho.mqtt import client as mqttclient


engine_to_eval_queue = Queue()
eval_to_engine_queue = Queue()

gun_thread_queue = Queue()
gun_to_engine_queue = Queue()

mqtt_vizhit_queue = Queue()
relay_mlai_queues = [Queue() , Queue()]

debug = False
onePlayerMode= False
noDupes = False
p1flag = False
p2flag = False
BROKER = 'broker.emqx.io'
# BROKER = '116.15.202.187'


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
            if not engine_to_eval_queue.empty():
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
        self.timeout = 60
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
                        start_time = perf_counter()
                        task = loop.sock_recv(self.conn, 1)
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
                        task = loop.sock_recv(self.conn, length - len(data))
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
                print("relay " + str(self.sn) + " disconnected")
                loop = asyncio.get_event_loop()
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
                success, timeout, text_received = await self.receive_message(self.timeout)

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


    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass
        

class GunLogicThread:

    def run(self):
        global debug

        p1gun = 0
        p1gunflag = False
        p2gun = 0
        p2gunflag = False
        p1vest = 0
        p1vestflag = False
        p2vest = 0
        p2vestflag = False

        while True:
            # if not gun_thread_queue.empty():                    
            #     msg = gun_thread_queue.get()
            #     hit = False
            #     currtime = time()

            #     if msg[1:] == 'KANA SHOT':
            #         if msg[0] == 1:
            #             if p2gunflag == True:
            #                 hit = True
            #                 p2gunflag = False
            #                 p1vestflag = False
            #             else:
            #                 p1vestflag = True
            #                 p1vest = currtime
            #         else:
            #             if p1gunflag == True:
            #                 hit = True
            #                 p1gunflag = False
            #                 p2vestflag = False
            #             else:
            #                 p2vestflag = True
            #                 p2vest = currtime

            #     if msg[1:] == 'SHOTS FIRED':
            #         if msg[0] == 1:
            #             if p2vestflag == True:
            #                 hit = True
            #                 p2vestflag = False
            #                 p1gunflag = False
            #             else:
            #                 p1gunflag = True
            #                 p1gun = currtime
            #         else:
            #             if p1vestflag == True:
            #                 hit = True
            #                 p1vestflag = False
            #                 p2gunflag = False
            #             else:
            #                 p2gunflag = True
            #                 p2gun = currtime

            #     if hit == True:
            #         x = {
            #             "player_id": msg[0],
            #             "action": "gun",
            #             "isHit": True
            #         }
            #         gun_to_engine_queue.put(json.dumps(x))

            # else:
            #     currtime = time()
                
            #     if currtime > p1gun + 0.2:
            #         x = {
            #             "player_id": 1,
            #             "action": "gun",
            #             "isHit": False
            #         }
            #         gun_to_engine_queue.put(json.dumps(x))
            #         p1gunflag = False

            #     if currtime > p2gun + 0.2:
            #         x = {
            #             "player_id": 2,
            #             "action": "gun",
            #             "isHit": False
            #         }
            #         gun_to_engine_queue.put(json.dumps(x))
            #         p2gunflag = False
                
            #     if currtime > p1vest + 0.2:
            #         p1vestflag = False

            #     if currtime > p2vest + 0.2:
            #         p2vestflag = False

            if not gun_thread_queue.empty():                    
                msg = gun_thread_queue.get()
                currtime = perf_counter()

                if onePlayerMode:

                    if msg[1:] == 'KANA SHOT':
                        if msg[0] == '1':
                            if p1gunflag == True:
                                x = {
                                    "player_id": '1',
                                    "action": "gun",
                                    "isHit": True
                                }
                                gun_to_engine_queue.put(x)
                                p1gunflag = False
                                p1vestflag = False

                                if debug:
                                    print("p1 vest fired in gun window")

                            else:
                                p1vestflag = True
                                p1vest = currtime

                                if debug:
                                    print("p1 vest flag set")

                    if msg[1:] == 'SHOTS FIRED':
                        if msg[0] == '1':
                            if p1vestflag == True:
                                x = {
                                    "player_id": '1',
                                    "action": "gun",
                                    "isHit": True
                                }
                                gun_to_engine_queue.put(x)
                                p1vestflag = False
                                p1gunflag = False

                                if debug:
                                    print("p1 gun fired in vest window")

                            else:
                                p1gunflag = True
                                p1gun = currtime

                                if debug:
                                    print("p1 gun flag set")
                else:
                    if msg[1:] == 'KANA SHOT':
                        if msg[0] == '1':
                            if p2gunflag == True:
                                x = {
                                    "player_id": '2',
                                    "action": "gun",
                                    "isHit": True
                                }
                                gun_to_engine_queue.put(x)
                                p2gunflag = False
                                p1vestflag = False
                            else:
                                p1vestflag = True
                                p1vest = currtime
                        else:
                            if p1gunflag == True:
                                x = {
                                    "player_id": '1',
                                    "action": "gun",
                                    "isHit": True
                                }
                                gun_to_engine_queue.put(x)
                                p1gunflag = False
                                p2vestflag = False
                            else:
                                p2vestflag = True
                                p2vest = currtime

                    if msg[1:] == 'SHOTS FIRED':
                        if msg[0] == 1:
                            if p2vestflag == True:
                                x = {
                                    "player_id": '1',
                                    "action": "gun",
                                    "isHit": True
                                }
                                gun_to_engine_queue.put(x)
                                p2vestflag = False
                                p1gunflag = False
                            else:
                                p1gunflag = True
                                p1gun = currtime
                        else:
                            if p1vestflag == True:
                                x = {
                                    "player_id": '2',
                                    "action": "gun",
                                    "isHit": True
                                }
                                gun_to_engine_queue.put(x)
                                p1vestflag = False
                                p2gunflag = False
                            else:
                                p2gunflag = True
                                p2gun = currtime

            else:
                currtime = perf_counter()
                
                if p1gunflag == True and currtime > p1gun + 1:
                    x = {
                        "player_id": '1',
                        "action": "gun",
                        "isHit": False
                    }
                    gun_to_engine_queue.put(x)

                    p1gunflag = False

                    if debug:
                        print("resetted p1 gun flag, considered miss")
                
                if p1vestflag == True and currtime > p1vest + 1:
                    p1vestflag = False

                    if debug:
                        print("resetted p1 vest flag")

                if p2gunflag == True and currtime > p2gun + 1:
                    x = {
                        "player_id": '2',
                        "action": "gun",
                        "isHit": False
                    }
                    gun_to_engine_queue.put(x)

                    p2gunflag = False

                    if debug:
                        print("resetted p2 gun flag, considered miss")
                
                if p2vestflag == True and currtime > p2vest + 1:
                    p2vestflag = False

                    if debug:
                        print("resetted p2 vest flag")


# This thread will read from the relay_mlai_queue and identify the actions from sensor data, then publish it to the visualiser via MQTT. 
# For now it just forwards data to the visualizer via MQTT.
class ClassificationThread:

    def __init__(self, sn):
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

        actions = ["reload", "shield", "hammer", "spear", "portal", "punch", "web", "logout"]
        buffer = [0]*(32*8)
        pointer = 0
        lastpacket = perf_counter()
        lastaction = perf_counter()
        isNewAction = False
        toPublish = False

        while True:
            if not relay_mlai_queues[self.sn - 1].empty():
                msg = relay_mlai_queues[self.sn - 1].get()

                if debug:
                    print("sensor reading get: " + msg)

                res = msg.strip("{}").split(",")

                isNewAction = True
                lastpacket = perf_counter()
                for i in res:
                    buffer[pointer] = i
                    pointer += 1
                    # here we have received all 32 packets
                    if pointer == 255:
                        if debug:
                            print("received " + str(pointer + 1) + "(full) packets, action to be identified")
                    
                        action = actions[predict_action(buffer) % 8]
                        toPublish = True
                        pointer = 0

            # if we do not receive a packet in 200ms we assume that there has been packet drop and send it for classification.
            elif perf_counter() > lastpacket + 0.2 and isNewAction:
                if pointer > 239:
                    if debug:
                        print("received " + str(pointer + 1) + " packets, action to be identified")

                    action = actions[predict_action(buffer) % 8]
                    toPublish = True
                    pointer = 0
                # if too many packets are dropped we just discard it to be safe
                else:
                    if debug:
                        print("received " + str(pointer + 1) + " packets, data discarded")

                    isNewAction = False
                    toPublish = False
                    pointer = 0

            if toPublish:
                # funky measure to stop actions that occur within 3s because they are likely to be misfires
                if perf_counter() > lastaction + 3.0:
                    x = {
                        "type": "QUERY",
                        "player_id": '1',
                        "action": action,
                    }
                    mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                    lastaction = perf_counter()

                    if debug:
                        print(f"CLASSIFICATION{self.sn}: motion data passed to viz:" + json.dumps(x))
                else:
                    if debug:
                        print(f"CLASSIFICATION{self.sn}: WARNING! Double action discarded")

                isNewAction = False
                toPublish = False

            
# This is the game engine. It receives hit confirmations via MQTT and updates the game state accordingly. If it is a hit (valid action) it passes the
# action and game state to the eval_client for verification. It then puts the updated game state on the draw queue.
class GameEngine:

    def __init__(self) -> None:
        self.game_state = GameState()


    def connect_mqtt(self):
        # Set Connecting Client ID
        client = mqttclient.Client(f'lasertagb01-engine')
        client.on_connect = self.on_connect
        # client.username_pw_set(username, password)
        client.connect(BROKER, 1883)
        return client


    def on_message(self, client, userdata, message):
        mqtt_vizhit_queue.put(json.loads(message.payload.decode("utf-8")))
        

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

        while True:
            if not gun_to_engine_queue.empty() or not mqtt_vizhit_queue.empty():
                if not gun_to_engine_queue.empty():
                    msg = gun_to_engine_queue.get()
                else:
                    # get actions from vizhit
                    msg = mqtt_vizhit_queue.get()

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
                        
                # we dont send our custom actions to the eval server
                if valid:
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

            # # worst case scenario we just spam guns 
            # elif relay1Disconnected == True or relay2Disconnected == True:
                
            #     if noDupes:
            #         if p1flag == True:
            #             if relay2Disconnected == True:
            #                 player_id = 2
            #             else:
            #                 continue

            #             if p2flag == True:
            #                 print("This statement should not be reached.")
            #             else:
            #                 p1flag = False
            #         else:
            #             if relay1Disconnected == True:
            #                 player_id = 1
            #             else:
            #                 continue

            #             if p2flag == True:
            #                 p1flag = False
            #             else:
            #                 p1flag = True
            #     else:
            #         if relay1Disconnected == True:
            #             player_id = 1
            #         else:
            #             continue

            #     x = {
            #         "player_id": player_id,
            #         "action": "gun",
            #         "isHit": True,
            #     }
            #     self.game_state.update(msg)

            #     x = {
            #         "player_id": player_id,
            #         "action": "gun",
            #         "isHit": True,
            #         "game_state": self.game_state.get_dict()
            #     }
            #     engine_to_eval_queue.put(json.dumps(x))

            #     # NOTE: THIS IS BLOCKING because we need verification from eval server, and we want to avoid desync
            #     eval_server_game_state = json.loads(eval_to_engine_queue.get()) 
                
            #     # overwrite our game state with the eval server's if ours is wrong
            #     x = {
            #         "type": "UPDATE",
            #         "player_id": msg["player_id"],
            #         "action": action,
            #         "isHit": msg["isHit"],
            #         "game_state": self.game_state.get_dict()
            #     }

            #     if debug:
            #         print("final update forwarded to viz:" + json.dumps(x))
            #     mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                    

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

if sys.argv[2] == "1":
    onePlayerMode = True

if sys.argv[3] == "1":
    noDupes = True


secret_key = bytes(str('1111111111111111'), encoding="utf8")  # Convert password to bytes

eval_client = EvalClientThread(host, port, secret_key)
relaycomms_client1 = RelayCommsThread(1)
relaycomms_client2 = RelayCommsThread(2)

classification_thread1 = ClassificationThread(1)
classification_thread2 = ClassificationThread(2)
gun_thread = GunLogicThread()
game_engine = GameEngine()

asyncio.create_task(eval_client.main)
asyncio.create_task(relaycomms_client1.main)
asyncio.create_task(relaycomms_client2.main)
# evalclient = Process(target=eval_client.run)
# relay1 = Process(target=relaycomms_client1.run)
# relay2 = Process(target=relaycomms_client2.run)
classification1 = Process(target=classification_thread1.run)
classification2 = Process(target=classification_thread2.run)
gun = Process(target=gun_thread.run)
engine = Process(target=game_engine.run)

# evalclient.start()
# relay1.start()
# relay2.start()
classification1.start()
classification2.start()
gun.start()
engine.start()

# evalclient.join()
# relay1.join()
# relay2.join()
classification1.join()
classification2.join()
gun.join()
engine.join()




