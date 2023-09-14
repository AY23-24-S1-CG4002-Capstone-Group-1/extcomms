1) run the eval server with command "python3 WebSocketServer.py"

2) Eval server hosts a Wesocket server listening on port 8001. The web interface is connected to this server

3) Eval server hoasts a TCP server to connect to "eval client" from Ultra96

4) To understand the code start from WebSocketServer.handler()
