import socket
import base64
import json
import queue


class TCPClient:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('0.0.0.0', 10000))
        

    def handle_relay(self, conn):
        while True:
            msg = conn.recv(1024).decode("utf-8")
            print("motion received put on queue: " + msg)
            data = json.loads(msg)
            if data["action"] == "logout":
                return 'QUIT'
            # mqtt_motion_queue.put(json.dumps(msg))

    
    def run(self):

        self.sock.listen()
        print("relay-ultra96 thread listening")

        while True:
            (conn, address) = self.sock.accept()
            # now do something with the clientsocket
            # in this case, we'll pretend this is a threaded server
            if self.handle_relay(conn) == 'QUIT':
                break


def main():
    relay_client = TCPClient()
    relay_client.run()


if __name__ == "__main__":
    main()
