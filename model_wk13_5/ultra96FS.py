'''
Enter 3 args: 
debug   : Prints debug messages
noDupes : 2p mode any player cannot go twice before the other, includes round system and eval server related safeguards
freePlay: No eval server

Note that this code does not run on Windows since it uses spawn instead of fork, which will throw an error. 
'''

import sys
import socket
import base64
import json
import asyncio
import atexit
import random
import queue

from engine import GameState
from predict import predict_action

from time import perf_counter
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from multiprocessing import Process, Queue, Lock
from paho.mqtt import client as mqttclient
from socket import SHUT_RDWR

from pynq import Overlay

engine_to_eval_queue = Queue()
eval_to_engine_queue = Queue()

gun_process_queue = Queue()
to_engine_queue = Queue()

relay_mlai_queues = [Queue() , Queue()]

dma_lock = Lock()

debug = False
noDupes = False
freePlay = False
# BROKER = 'broker.emqx.io'
# BROKER = '54.244.173.190' # This is broker.emqx.io but we faced some issues with DNS resolution once so it's safer to use this.
# BROKER = 'test.mosquitto.org'
BROKER = '116.15.202.187'

# period of time for which actions are blocked after an action goes through, player specific
DOUBLE_ACTION_WINDOW = 3.0 
# period of time for which gun/vest will wait for the opposing vest/gun to fire and count as a hit
GUN_WINDOW = 0.3
# period of time for which the classification thread will wait for further sensor readings before deeming it to be the end of transmission
SENSOR_WINDOW = 0.5

# strings sent from relay
HIT_MESSAGE = "KANA SHOT"
SHOOT_MESSAGE = "SHOTS FIRED"

# period of time for which game engine will wait for the second player before predicting an action
SECOND_PLAYER_TIMEOUT = 30
# when there is a late response from the eval server (indicative of a queued action) this is the period of time for which actions from the queue will be ignored
NEW_ROUND_GUARD_WINDOW = 1.0


def printError(msg): print("\033[41m\033[37m{}\033[00m" .format(msg))
def printInfo(msg): print("\033[42m\033[92m{}\033[00m" .format(msg))
def printP1(msg): print("\033[93m{}\033[00m" .format(msg))
def printP1Info(msg): print("\033[93m\033[42m{}\033[00m" .format(msg))
def printP1Error(msg): print("\033[93m\033[41m{}\033[00m" .format(msg))
def printP2(msg): print("\033[96m{}\033[00m" .format(msg))
def printP2Info(msg): print("\033[96m\033[42m{}\033[00m" .format(msg))
def printP2Error(msg): print("\033[96m\033[41m{}\033[00m" .format(msg))
def printEngineP1(msg): print("\033[47m\033[30m[ENGINE]\033[00m \033[93m{}\033[00m" .format(msg))
def printEngineP2(msg): print("\033[47m\033[30m[ENGINE]\033[00m \033[96m{}\033[00m" .format(msg))
def printEngineError(msg): print("\033[47m\033[30m[ENGINE]\033[00m \033[41m\033[37m{}\033[00m" .format(msg))


'''
This process reads from the engine_to_eval_queue and sends all valid actions to the eval server.
'''
class EvalClientProcess:
    
    def __init__(self, ip_addr, port, secret_key):
        self.ip_addr        = ip_addr
        self.port           = port
        self.secret_key     = secret_key
  
        self.timeout        = 900000
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

        if debug:
            print("[EVALUATION CLIENT] Received: " + msg)

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


    def cleanup(self):
        try:
            if self.port is not None:
                self.port.shutdown(SHUT_RDWR)
                self.port.close()
                self.port = None
            self.sock.close()
        except Exception as e:
            printError("[EVALUATION CLIENT] Failed to shutdown.")


    async def main(self):
        await self.send_message("hello") 

        while True:
            msg = json.loads(engine_to_eval_queue.get()) # get valid actions from engine and send it to eval server

            x = {
                "player_id": msg["player_id"],
                "action": msg["action"],
                "game_state": msg["game_state"]
            }

            if debug:
                print("[EVALUATION CLIENT] Sending JSON to eval server:" + json.dumps(x))

            await self.send_message(json.dumps(x))

            try:
                success, timeout, text_received = await self.receive_message(self.timeout)

                if success:
                    eval_to_engine_queue.put(text_received)
                else:
                    printError("[EVALUATION CLIENT] ERROR! NO REPLY RECEIVED FROM EVAL_SERVER!")
            except:
                printError("[EVALUATION CLIENT] ERROR! INVALID REPLY RECEIVED FROM EVAL_SERVER!")
                eval_to_engine_queue.put("ERROR")


    def run(self):
        try:
            atexit.register(self.cleanup)
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass




'''
This process receives data from the relay node via TCP and sends it to the gun/classification process.
'''
class RelayCommsProcess:
    
    def __init__(self, sn):
        self.timeout = None
        self.is_running = True
        self.sn = sn
        self.port = 10000 + self.sn
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', self.port)) # Binds to p1 relay on 10001, p2 relay on 10002


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
                printError("[RELAY " + str(self.sn) + "] disconnected")
                self.conn, self.addr = await loop.sock_accept(self.sock)
                printInfo("[RELAY " + str(self.sn) + "] connected")
            except asyncio.TimeoutError:
                timeout = -1
        else:
            timeout = -1

        return success, timeout, msg


    async def main(self):
        while True:
            if not self.is_running:
                return
            self.sock.listen(1)
            self.sock.setblocking(False)

            loop = asyncio.get_event_loop()
            self.conn, self.addr = await loop.sock_accept(self.sock)
            printInfo("[RELAY " + str(self.sn) + "] CONNECTED")
            while True:
                success, timeout, text_received = await self.receive_message(self.timeout)

                if text_received == '':
                    # invalid data
                    pass
                elif text_received == HIT_MESSAGE or text_received == SHOOT_MESSAGE:
                    # if debug:
                    #     print("[RELAY " + str(self.sn) + "] Received: " + text_received + " , put on gun queue")
                    gun_process_queue.put(str(self.sn) + text_received)
                else:
                    # if debug:
                    #     print("[RELAY " + str(self.sn) + "] Received: " + text_received + " , put on mlai queue")
                    relay_mlai_queues[self.sn - 1].put(text_received)


    def cleanup(self):
        try:
            if self.port is not None:
                self.port.shutdown(SHUT_RDWR)
                self.port.close()
                self.port = None
            self.sock.close()
        except Exception as e:
            printError("[RELAY " + str(self.sn) + "] Failed to shutdown.")


    def run(self):
        atexit.register(self.cleanup)
        asyncio.run(self.main())
        



'''
This process reads from the gun queue. By default it has no timeout. This implementation is based off of queues and timeouts,
which is less intuitive than the polling and timer version.
When it receives a vest fired, it checks the fire time of the opposing gun.
    If it was within the GUN_WINDOW, then it is counted as a hit.
    If it was not, then updates the hit time of the vest. 
When it receives a gun fired, it checks the hit time of the opposing vest. 
    If it was within the GUN_WINDOW, then it is counted as a hit.
    If it was not, then it updates the fire time of this gun. The queue timeout is then set as the GUN_WINDOW.
        If it times out, then it is a miss. 
*(Note) For all of these cases, if another gun's GUN_WINDOW is still active then the timeout is set to its timeout instead.
'''
class GunLogicProcess:

    def run(self):
        p1gun = 0
        p2gun = 0
        p1vest = 0
        p2vest = 0
        p1gunflag = False
        p2gunflag = False
        timeout = None

        while True: 
            try:            
                msg = gun_process_queue.get(timeout = timeout)
                currtime = perf_counter()

                if msg[1:] == HIT_MESSAGE:
                    if msg[0] == '1':
                        if currtime < p2gun + GUN_WINDOW:
                            x = {
                                "player_id": '2',
                                "action": "gun",
                                "isHit": True
                            }
                            to_engine_queue.put(x)
                            p2gunflag = False
                            if p1gunflag:
                                timeout = p1gun + GUN_WINDOW - currtime
                            else:
                                timeout = None
                        else:
                            p1vest = currtime
                            if p1gunflag:
                                timeout = p1gun + GUN_WINDOW - currtime
                            else:
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
                            if p2gunflag:
                                timeout = p2gun + GUN_WINDOW - currtime
                            else:
                                timeout = None
                        else:
                            p2vest = currtime
                            if p2gunflag:
                                timeout = p2gun + GUN_WINDOW - currtime
                            else:
                                timeout = None

                elif msg[1:] == SHOOT_MESSAGE:
                    if msg[0] == '1':
                        if currtime < p2vest + GUN_WINDOW:
                            x = {
                                "player_id": '1',
                                "action": "gun",
                                "isHit": True
                            }
                            to_engine_queue.put(x)
                            if p2gunflag:
                                timeout = p2gun + GUN_WINDOW - currtime
                            else:
                                timeout = None
                        else:
                            p1gun = currtime
                            p1gunflag = True
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
                            if p1gunflag:
                                timeout = p1gun + GUN_WINDOW - currtime
                            else:
                                timeout = None
                        else:
                            p2gun = currtime
                            p2gunflag = True
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
                    if p2gunflag:
                        timeout = p2gun + GUN_WINDOW - currtime
                    else:
                        timeout = None

                if p2gunflag and currtime > p2gun + GUN_WINDOW:
                    x = {
                        "player_id": '2',
                        "action": "gun",
                        "isHit": False
                    }
                    to_engine_queue.put(x)
                    p2gunflag = False
                    if p1gunflag:
                        timeout = p1gun + GUN_WINDOW - currtime
                    else:
                        timeout = None




'''
This process will read from the relay_mlai_queue and identify the actions from sensor data, then publish it to the visualiser via MQTT. 
Default timeout is none but when it receives packets it is set to the SENSOR_WINDOW. After an action has been identified the timeout is reset back to none.
If it receives 30 packets it proceeds.
If timeout:
    If it receives more than 28 packets it proceeds.
    Otherwise it discards it.
There is a safeguard to block any action published within the DOUBLE_ACTION_WINDOW of each other from the same player since it is likely that the onset 
detection has fired twice by accident.
'''
class ClassificationProcess:

    def __init__(self, sn, ol):
        self.ol = ol
        self.sn = sn


    def connect_mqtt(self):
        client = mqttclient.Client(f'lasertagb01-class-{self.sn}')
        client.on_connect = self.on_connect
        client.connect(BROKER, 1883)
        return client
    

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

            
    def run(self):
        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        actions = ["portal", "web", "shield", "hammer", "grenade", "spear", "reload", "punch",  'logout', 'none']
        buffer = [0]*(30*8)
        pointer = 0
        lastaction = perf_counter()
        blockwindow = DOUBLE_ACTION_WINDOW
        timeout = None
        toPublish = False

        while True:
            try:
                msg = relay_mlai_queues[self.sn - 1].get(timeout = timeout)

                if debug:
                    if self.sn == 1:
                        printP1("[P1 CLASSIFICATION] Sensor reading get: " + msg)
                    else:
                        printP2("[P2 CLASSIFICATION] Sensor reading get: " + msg)

                res = msg.strip("{}").split(",")

                for i in res:
                    buffer[pointer] = i
                    pointer += 1
                    # here we have received at least 30 packets
                    if pointer == 239:
                        if debug:
                            if self.sn == 1:
                                printP1("[P1 CLASSIFICATION] Received " + str(pointer + 1) + "(full) packets, action to be identified")
                            else:
                                printP2("[P2 CLASSIFICATION] Received " + str(pointer + 1) + "(full) packets, action to be identified")

                        dma_lock.acquire()
                        action = actions[predict_action(buffer, 0, self.ol)]
                        dma_lock.release()

                        toPublish = True
                        pointer = 0
                        timeout = None
                    else:
                        timeout = SENSOR_WINDOW

            except:
                # if we do not receive a packet in 200ms we assume that there has been packet drop and send it for classification.
                if pointer > 223:
                    if debug:
                        if self.sn == 1:
                            printP1("[P1 CLASSIFICATION] Received " + str(pointer + 1) + " packets, action to be identified")
                        else:
                            printP2("[P2 CLASSIFICATION] Received " + str(pointer + 1) + " packets, action to be identified")

                    dma_lock.acquire()
                    action = actions[predict_action(buffer, 0, self.ol)]
                    dma_lock.release()

                    toPublish = True
                    pointer = 0
                # if too many packets are dropped we just discard it to be safe
                else:
                    if debug:
                        if self.sn == 1:
                            printP1Error("[P1 CLASSIFICATION] Received " + str(pointer + 1) + " packets, data discarded")
                        else:
                            printP2Error("[P2 CLASSIFICATION] Received " + str(pointer + 1) + " packets, data discarded")

                    toPublish = False
                    pointer = 0
                timeout = None

            if toPublish:
                # funky measure to stop actions that occur within 3s because they are likely to be misfires
                if perf_counter() > lastaction + blockwindow:
                    x = {
                        "type": "QUERY",
                        "player_id": self.sn,
                        "action": action,
                    }
                    mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
                    lastaction = perf_counter()

                    if debug:
                        if self.sn == 1:
                            printP1Info("[P1 CLASSIFICATION] Motion data passed to viz:" + json.dumps(x))
                        else:
                            printP2Info("[P2 CLASSIFICATION] Motion data passed to viz:" + json.dumps(x))
                else:
                    if debug:
                        if self.sn == 1:
                            printP1Error("[P1 CLASSIFICATION] WARNING! Double action discarded")
                        else:
                            printP2Error("[P2 CLASSIFICATION] WARNING! Double action discarded")
                
                buffer = [0]*(30*8)
                toPublish = False
                # if action is hammer then we block for an extended period of time because it is likely to triple fire
                if action == 3:
                    blockwindow = 1.5 * DOUBLE_ACTION_WINDOW
                else:
                    blockwindow = DOUBLE_ACTION_WINDOW




'''
This is the game engine. It receives hit confirmations via MQTT and updates the game state accordingly. If it is a hit (valid action) it passes the
action and game state to the eval_client for verification. It then puts the updated game state on the draw queue.
(Note) This implementation will completely brick/jam in the case of a double action from the same player, or an action from p2 in 1p eval. This is because
we are always waiting for a reply from the eval server that will never come in those scenarios. This is a conscious design decision since due to the noDupes
system we should never ever encounter such a scenario unless the hardware fails to reconnect, in which case it is already a catastrophic failure.

A failsafe has been added to the game engine. This failsafe operates on the following assumptions:
- At least one glove/gun is still connected.
- The first player goes within the first 20-30s, since otherwise the 30s timeout will not be in time before eval server timeout.
- Classified actions are assumed to be correct.
When the first player goes, a 30s timeout starts, after which the game engine will automatically send an action to the game server to prevent timeout and
this will keep the round system working. This action defaults to gun since it comprises most of the actions. When the system times out, a timeout flag will 
be set for that player. If a gun action is received later on from that player then it is assumed that the gun is working and it will start to predict actions
instead. The system does try to keep track of classified actions to predict future actions. On round 24 and 25 it will always predict logout.

If the eval server takes more than 2s to reply it is likely that the action had been queued up. As a result we will discard all actions received in the next 500ms
since they are likely to have been misfires that were queued up as well.
'''
class GameEngine:

    def __init__(self):
        self.game_state = GameState()


    def connect_mqtt(self):
        client = mqttclient.Client(f'lasertagb01-engine')
        client.on_connect = self.on_connect
        client.connect(BROKER, 1883)
        return client


    def on_message(self, client, userdata, message):
        to_engine_queue.put(json.loads(message.payload.decode("utf-8")))
        

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)


    def getActionList(self):
        actions = ["portal", "web", "shield", "hammer", "grenade", "spear", "reload", "punch"]
        actions.extend(actions)
        return actions


    def run(self):
        p1flag = False
        p2flag = False

        # variables to handle timeout prediction, flags for having timed out and predict type
        p1timeout = False
        p2timeout = False
        p1ptype = "gun"
        p2ptype = "gun"
        timeout = None
        lastaction = perf_counter()
        roundcount = 1
        actions = ["portal", "web", "shield", "hammer", "grenade", "spear", "reload", "punch",  'logout', 'none']
        p1actions = self.getActionList()
        p2actions = self.getActionList()
        p1guncount = 0
        p2guncount = 0

        freeze_time = perf_counter()

        mqttclient = self.connect_mqtt()
        mqttclient.loop_start()

        mqttclient.subscribe("lasertag/vizhit")
        mqttclient.on_message = self.on_message

        while True:
            try:
                msg = to_engine_queue.get(timeout = timeout)

                if debug:
                    if msg["player_id"] == "1":
                        printEngineP1("Update:" + str(msg))
                    else:
                        printEngineP2("Update:" + str(msg))

                # if we check for dupes we do not accept dupes from the same player
                if noDupes:
                    
                    # if we detect a long response time from eval server, odds are the the action was queued up due to a misfire.
                    # We will then update the freeze_time to the time when the reply was received, and then consequently we block
                    # all following actions within a short time frame since they are likely also misfires that have been queued up.
                    if perf_counter() < freeze_time + NEW_ROUND_GUARD_WINDOW:
                        continue

                    if msg["action"] == "none":
                        # none action will not start 30s timeout
                        if p1flag == False and p2flag == False:
                            pass
                        # we continue the active timeout when none action is received
                        else:
                            timeout = SECOND_PLAYER_TIMEOUT + lastaction - perf_counter() 

                    else:
                        player_id = msg["player_id"]
                        action = msg["action"]

                        # if player timeout is in effect by default we predict gun. If we receive a gun from them then we swap to
                        # predicting actions and vice versa
                        if player_id == "1" and p1timeout == True:
                            if action == "gun" and p1ptype == "gun":
                                p1ptype = "action"
                            if action in actions and p1ptype == "action":
                                p1ptype = "gun"

                        if player_id == "2" and p2timeout == True:
                            if action == "gun" and p2ptype == "gun":
                                p2ptype = "action"
                            if action in actions and p2ptype == "action":
                                p2ptype = "gun"

                        # if a player is blocked we discard the action 
                        if player_id == "1" and p1flag == True:
                            timeout = SECOND_PLAYER_TIMEOUT + lastaction - perf_counter() 
                            continue
                        if player_id == "2" and p2flag == True:
                            timeout = SECOND_PLAYER_TIMEOUT + lastaction - perf_counter() 
                            continue

                        # never allow a player to send 2 consecutive actions in the same round (2 player)
                        if player_id == "1":
                            if p2flag == True:
                                p2flag = False
                                timeout = None
                                roundcount += 1
                            else:
                                p1flag = True
                                timeout = SECOND_PLAYER_TIMEOUT
                            if action in p1actions:
                                p1actions.remove(action)
                            if action == "gun":
                                p1guncount += 1
                                if p1guncount >= 7:
                                    p1ptype = "action"
                        else:
                            if p1flag == True:
                                p1flag = False
                                timeout = None
                                roundcount += 1
                            else:
                                p2flag = True
                                timeout = SECOND_PLAYER_TIMEOUT
                            if action in p2actions:
                                p2actions.remove(action)
                            if action == "gun":
                                p2guncount += 1
                                if p2guncount >= 7:
                                    p2ptype = "action"

                # update gamestate
                valid = self.game_state.update(msg)

                action = msg["action"]
                
                # we handle timeoutactions here
                # note that timeout actions are always going to be the 2nd action and start of the new round
                # if action comes in just before timeout we are fine, if action comes in just after timeout then it will eat into the next round so
                # we block for a while
                if action == "guntimeout":
                    freeze_time = perf_counter()
                    action = "gun"
                elif action == "actiontimeout":
                    freeze_time = perf_counter()
                    if msg["player_id"] == "1":
                        if p1actions:
                            action = random.choice(p1actions)
                        else:
                            action = "web"
                    else:
                        if p2actions:
                            action = random.choice(p2actions)
                        else:
                            action = "web"

                x = {
                    "player_id": msg["player_id"],
                    "action": action,
                    "game_state": self.game_state.get_dict()
                }
                
                # we dont send our actions to eval server in freeplay, or custom actions to the eval server at all
                if not freePlay and not msg["action"] == "none":
                    engine_to_eval_queue.put(json.dumps(x))

                    try:
                        send_time = perf_counter()

                        # NOTE: THIS IS BLOCKING because we need verification from eval server, and we want to avoid desync
                        eval_server_game_state = json.loads(eval_to_engine_queue.get())

                        response_time = perf_counter() - send_time
                        if response_time > 2.0:
                            freeze_time = perf_counter()

                        # overwrite our game state with the eval server's if ours is wrong
                        if eval_server_game_state != self.game_state.get_dict(): 
                            printEngineError(" WARNING: EVAL SERVER AND ENGINE DESYNC, RESYNCING")
                            self.game_state.overwrite(eval_server_game_state)
                        
                    except:
                        printEngineError("ERROR! INVALID JSON RECEIVED FROM EVAL SERVER")

                # keep track of last action time to be able to update timeout, assumption is that it is near instantaneous from this point
                # since its not blocked by eval server
                lastaction = perf_counter()

                if msg["action"] == 'none':
                    action = "none"
                else:
                    # only draw valid actions
                    if valid: 
                        action = msg["action"]
                    # This will print an invalid message on visualiser, and is for the case when the player attempts to throw
                    # a grenade without any remaining, shielding while they still have a shield, or reloading while they still
                    # have bullets. Note that the action action itself was already sent to eval server
                    else: 
                        action = "invalid"

                # put updated game state on queue for drawing
                x = {
                    "type": "UPDATE",
                    "player_id": msg["player_id"],
                    "action": action,
                    "isHit": msg["isHit"],
                    "game_state": self.game_state.get_dict()
                }

                if debug:
                    if msg["player_id"] == "1":
                        printEngineP1("Final update forwarded to viz:" + json.dumps(x))
                    else:
                        printEngineP2("Final update forwarded to viz:" + json.dumps(x))
                        
                mqttclient.publish("lasertag/vizgamestate", json.dumps(x))
            
            # When we timeout (which only happens if noDupes is true) then we check the flags to see which player has not gone yet
            # and generate a gun action by default.
            except queue.Empty:
                if p1flag:
                    if roundcount >= 24:
                        x = {
                            "player_id": '2',
                            "action": "logout",
                            "isHit": True
                        }
                    elif p2ptype == "gun":
                        x = {
                            "player_id": '2',
                            "action": "guntimeout",
                            "isHit": True
                        }
                    else:
                        x = {
                            "player_id": '2',
                            "action": "actiontimeout",
                            "isHit": True
                        }
                    to_engine_queue.put(x)
                    p2timeout = True
                    printEngineError("TIMEOUT: ACTION PREDICTED FOR P2")
                        
                else:
                    if roundcount >= 24:
                        x = {
                            "player_id": '1',
                            "action": "logout",
                            "isHit": True
                        }
                    elif p1ptype == "gun":
                        x = {
                            "player_id": '1',
                            "action": "guntimeout",
                            "isHit": True
                        }
                    else:
                        x = {
                            "player_id": '1',
                            "action": "actiontimeout",
                            "isHit": True
                        }
                    to_engine_queue.put(x)
                    p1timeout = True
                    printEngineError("TIMEOUT: ACTION PREDICTED FOR P1")

                timeout = None




if sys.argv[1] == "1":
    debug = True

if sys.argv[2] == "1":
    noDupes = True

if sys.argv[3] == "1":
    freePlay = True

if not freePlay:
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

    eval_client = EvalClientProcess(host, port, secret_key)
    evalclient = Process(target=eval_client.run)
    evalclient.start()

ol = Overlay("action.bit")

relaycomms_client1 = RelayCommsProcess(1)
relaycomms_client2 = RelayCommsProcess(2)
classification1 = ClassificationProcess(1, ol)
classification2 = ClassificationProcess(2, ol)
gun_logic = GunLogicProcess()
game_engine = GameEngine()

relay1 = Process(target=relaycomms_client1.run)
relay2 = Process(target=relaycomms_client2.run)
classification1 = Process(target=classification1.run)
classification2 = Process(target=classification2.run)
gun = Process(target=gun_logic.run)
engine = Process(target=game_engine.run)

relay1.start()
relay2.start()
gun.start()
engine.start()
classification1.start()
classification2.start()

try:
    # using a queue to block forever so I don't need to poll
    block = Queue()
    block.get()
except KeyboardInterrupt:
    relay1.terminate()
    relay2.terminate()
    gun.terminate()
    engine.terminate()
    classification1.terminate()
    classification2.terminate()
    if not freePlay:
        evalclient.terminate()
    printInfo("[MAIN] Program terminated successfully.")
