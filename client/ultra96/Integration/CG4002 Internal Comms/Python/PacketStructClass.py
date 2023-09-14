# Hello Packet Format
HELLO_PACKET_FORMAT = "BBHHHHHHHHBB"

# Hello Packet Struct
class HelloPacket:
    def __init__(self, packet_id):
        self.device_id = 0
        self.packet_id = packet_id
        self.padding_1 = 0
        self.padding_2 = 0
        self.padding_3 = 0
        self.padding_4 = 0
        self.padding_5 = 0
        self.padding_6 = 0
        self.padding_7 = 0
        self.padding_8 = 0
        self.padding_9 = 0
        self.checksum = 0
    

class AckPacket:
    def __init__(self, packet_id):
        self.device_id = 0
        self.packet_id = packet_id
        self.padding_1 = 0
        self.padding_2 = 0
        self.padding_3 = 0
        self.padding_4 = 0
        self.padding_5 = 0
        self.padding_6 = 0
        self.padding_7 = 0
        self.padding_8 = 0
        self.padding_9 = 0
        self.checksum = 0

