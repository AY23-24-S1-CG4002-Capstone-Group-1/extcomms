import socket
import json
import sshtunnel
import paramiko

class RelayClient:

    def __init__(self, sn):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sn = int(sn)


    def send_message(self, msg):
        self.sock.sendall(bytes(msg, encoding="utf-8"))

    
    def run(self):
        # stu tunnel
        tunnel1 = sshtunnel.SSHTunnelForwarder(
            ('makerslab-fpga-01.d2.comp.nus.edu.sg', 22),
            ssh_username = 'xilinx',
            ssh_password = "xilinx",
            remote_bind_address = ('192.168.3.1', 10000 + self.sn),
            local_bind_address = ('127.0.0.1', 10000)
        )

        tunnel1.start()
        print("sshtunnel1 connected")

        self.sock.connect(('127.0.0.1', tunnel1.local_bind_port))

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
