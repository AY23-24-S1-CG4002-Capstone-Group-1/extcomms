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

# Design choices
This program was written using multiprocessing and uses no polling, only blocking queues and timeouts to minimise CPU load.
```ultra96FS.py``` is pretty well documented, see it for more information.
