import socket
import json

class RelayClient:

    def __init__(self, sn):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sn = int(sn)


    def send_message(self, msg):
        self.sock.sendall(bytes(msg, encoding="utf-8"))

    
    def run(self):
        self.sock.connect(('makerslab-fpga-01.d2.comp.nus.edu.sg', 10000 + self.sn)) 

        while True:
            command = input("Enter command: ")

            if command == "q":
                break
            else:
                x = {
                    "player_id": 1,
                    "action": command,
                }
                self.send_message(json.dumps(x))
                print("sent:" + json.dumps(x))


def main():
    sn = input("Enter player number:")
    relay_client = RelayClient(sn)
    relay_client.run()


if __name__ == "__main__":
    main()
