import struct
import crc8

P1_VEST_DEVICE_ID = 2


# Define the struct format string
pkt_format = 'BBHHHHHHHHBB'
cal_CRC8_pkt_format = 'BBHHHHHHHHB'

# Create a class to represent the struct
class HelloPkt:
    def __init__(self, deviceID):
        self.deviceID = deviceID
        self.packetID = 0xE1
        self.message = 53110
        self.padding1 = 0
        self.padding2 = 0
        self.padding3 = 0
        self.padding4 = 0
        self.padding5 = 0
        self.padding6 = 0
        self.padding7 = 0
        self.padding8 = 0
        self.crcChecksum = 0
    
    def pack(self):
        return struct.pack(pkt_format, 
                           self.deviceID,
                           self.packetID, 
                           self.message, 
                           self.padding1, 
                           self.padding2, 
                           self.padding3, 
                           self.padding4, 
                           self.padding5, 
                           self.padding6, 
                           self.padding7, 
                           self.padding8, 
                           self.crcChecksum)
    
    def packForCRC8(self):
        return struct.pack(cal_CRC8_pkt_format, 
                    self.deviceID,
                    self.packetID, 
                    self.message, 
                    self.padding1, 
                    self.padding2, 
                    self.padding3, 
                    self.padding4, 
                    self.padding5, 
                    self.padding6, 
                    self.padding7, 
                    self.padding8)
    
    def unpack(data):
        unpacked_data = struct.unpack(pkt_format, data)
        return unpacked_data
    
    def print(self):
        print(self.deviceID, self.packetID, self.message, self.crcChecksum)  
    
# def prepHelloPkt(helloPkt):
#     bytePtk = helloPkt.packForCRC8
#     helloPkt.crcChecksum = calculateCRC8(bytePtk)

def calculateCRC8(dataNoCRC):
    hash = crc8.crc8()
    hash.reset()
    hash.update(dataNoCRC)
    calCRC8 = hash.digest()
    return calCRC8[0]

def prepHelloPkt(HelloPkt, deviceID, calculateCRC8):
    helloPkt = HelloPkt(deviceID)
    helloPkt.crcChecksum = calculateCRC8(helloPkt.packForCRC8())
    ptk = helloPkt.pack()
    return ptk

# if __name__=='__main__':
#     # Hello Packet in byte form to be sent
#     ptk = prepHelloPkt(HelloPkt, P1_VEST_DEVICE_ID, calculateCRC8)
#     # Tuple of hello packet
#     hPkt = HelloPkt.unpack(ptk)
#     print(hPkt)