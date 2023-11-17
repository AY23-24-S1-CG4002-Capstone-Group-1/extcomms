# Overview
This is the external comms portion that I did for my CG4002 capstone project.

# Directories
- ```html```: Eval server frontend code provided by mod
- ```server```: Eval server backend code provided by mod
- ```model_wk13_5```: The code used to run the final wk13 eval

# Files
- ```brokertest.py```: Test file used to test the latency of brokers
- ```mqttbrokertimings.txt```: Txt file containing the broker latencies
- ```engine.py```: Python file containing game logic
- ```predict.py```: Python file containing the HWAI function
- ```standardisations.py```: Extension of HWAI stuff used for preprocessing
- ```relay-int.py```: Mock relay used to test remotely without hardware
- ```ultra96FS.py```: The main program that runs on the Ultra96. Functionally identical to the one in ```model_wk13_5```, but with more documentation.

# Processes Overview
The Python ```multiprocessing``` library is used to start 6-7 processes. (The EvalClient  is not started in freeplay.) The processes are as follows:
- ```RelayClient```, the client that will communicate via TCP with the relay nodes. There are two of these processes, one for each player. Each process will send messages from the gun and vests to the GunLogic process and send motion data to their respective Classification process.
- ```Classification```, for which there are two processes, each of which will receive sensor data forwarded from its RelayClient. When receiving sensor data, it writes it into a buffer. 
Default timeout is none but when it receives packets timeout is set to the SENSOR_WINDOW. After an action has been identified the timeout is reset back to none.
If it receives 30 packets it proceeds with classification
On timeout, if it received more than 28 packets it proceeds with classification, otherwise it discards it.
After an action has been classified, if it is within the DOUBLE_ACTION_WINDOW of the previous action, it will be discarded since it is likely to have been a misfire. This window is extended after identifying a hammer action as well, since it even has a tendency to triple fire. Otherwise it will be sent via MQTT to the visualisers by publishing to lasertag/vizgamestate, and the buffer will be reset. All messages published from here have the type query. The visualisers will check if the opponent is visible on screen and reply if it is a hit or miss via lasertag/vizhit.
- ```GunLogic```, which takes in gun and vest messages from both players and determines if the guns hit or miss. This process reads from the gun queue. By default it has no timeout. This implementation is based on queues and timeouts. The in depth explanation can be found in the repo.
The result will be sent to the engine via the to_engine_queue.
- ```GameEngine```, the game engine itself. This will subscribe to lasertag/vizhit and put all replies from the visualiser on the to_engine_queue, which is also the same queue accessed by the GunLogic process. The engine reads from this queue and updates the game state based on hits and misses. 
If it is not in freeplay mode, it then sends the updated game state to the EvalClient for verification and waits for the reply. If it has been desynced from the evaluation server, it will overwrite its current game state. 
Finally, it will publish to lasertag/vizgamestate with the type update. The visualisers will draw the animations and update the UI based on these messages. The game engine also has several guards in place during evaluation, which can be found in section 6.6.
- ```EvalClient```, the client that communicates via TCP with the evaluation server. It receives the JSON containing the player_id, action and game_state from the GameEngine, sends it to the eval server, waits for the reply containing the correct game_state, then sends it back to the GameEngine. Since the GameEngine blocks while waiting for the reply, the EvalClient effectively runs sequentially with the GameEngine by design. The EvalClient is not started in freeplay.


# Design choices
This program was written using multiprocessing and uses no polling, only blocking queues and timeouts to minimise CPU load.
```ultra96FS.py``` is pretty well documented, see it for more information.
