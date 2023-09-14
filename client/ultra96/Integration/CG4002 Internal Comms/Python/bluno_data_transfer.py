# Import Libraries
from bluepy.btle import Peripheral, UUID, DefaultDelegate
import threading
import sys
import time
from PacketStructClass import HelloPacket, AckPacket
import CRC8Packet
import struct

hasBlunoRespond1 = False
hasSentResponseAck1 = False
hasBlunoRespond2 = False
hasSentResponseAck2 = False


NODE_DEVICE_ID = 0
BLUNO_1_DEVICE_ID = 1
BLUNO_2_DEVICE_ID = 2
BLUNO_3_DEVICE_ID = 3


HELLO_PACKET_ID = 0
CONN_EST_PACKET_ID = 1
ACK_PACKET_ID = 2
NAK_PACKET_ID = 3
DATA_PACKET_ID = 4

count1 = 0
count2 = 0
count3 = 0

ch1 = None
ch2 = None
ch3 = None

# MAC Address
Bluno1_MAC_Address = "D0:39:72:E4:93:BC"
Bluno2_MAC_Address = "D0:39:72:E4:80:A8"
Bluno3_MAC_Address = "D0:39:72:E4:91:AC"


helloPacketReceived1 = False
helloPacketReceived2 = False
helloPacketReceived3 = False
connPacketReceived1 = False
connPacketReceived2 = False
connPacketReceived3 = False


dataReceived =[0] * 20
isAcknowledgeMessage = False


# Function to connect to Bluno 1 and send data.
def Bluno1():
    while True:
        global helloPacketReceived1
        global connPacketReceived1

        global ch1
        print("Connecting to device 1...")

        bluno, ch1 = connectToBLE1()
        print("Device 1 connected")
        
        print("START Request Sent")
        ch1.write(CRC8Packet.pack_data(HelloPacket(HELLO_PACKET_ID)))
        
        while True:
            try:
                global count1
                while True:
                    if bluno.waitForNotifications(10): # calls handleNotification()
                        
                        
                        if ((helloPacketReceived1 == True) and (connPacketReceived1 == False)):
                            ch1.write(CRC8Packet.pack_data(HelloPacket(CONN_EST_PACKET_ID)))

                        elif (helloPacketReceived1 and connPacketReceived1 and (count1 == 0)):
                            print("Connection Established for Bluno 1")                
                            count1 += 1
            except Exception as e:
                print(f"An error occurred: {e}")
                
                helloPacketReceived1 = False
                connPacketReceived1 = False
                # bluno, ch1 = connectToBLE1()
                break
            # finally:
            #     bluno.disconnect()

def connectToBLE1():
    # Connect to Bluno1
    try:
        bluno = Peripheral(Bluno1_MAC_Address, "public")
        bluno.setDelegate(SensorsDelegate1())
    
        # Retrieve Service and Characteristics
        svc = bluno.getServiceByUUID("dfb0")
        ch = svc.getCharacteristics("dfb1")[0]
        

        return (bluno, ch)
    except Exception as e:
        print("Unable to connect to Bluno 1...")

    # Establish Delegate to handle notification
    
    return connectToBLE1()

# Function to connect to Bluno 2 and send data
def Bluno2():
    while True:
        global helloPacketReceived2
        global connPacketReceived2

        global ch2
        print("Connecting to device 2...")

        bluno, ch2 = connectToBLE2()
        print("Device connected 2")


        print("START Request Sent")
        ch2.write(CRC8Packet.pack_data(HelloPacket(HELLO_PACKET_ID)))
        while True:
            global count2
            try:
                while True:
                    if bluno.waitForNotifications(10): # calls handleNotification()
                        
                        
                        if ((helloPacketReceived2 == True) and (connPacketReceived2 == False)):
                            ch2.write(CRC8Packet.pack_data(HelloPacket(CONN_EST_PACKET_ID)))
                        
                        elif (helloPacketReceived2 and connPacketReceived2 and (count2 == 0)):
                            print("Connection Established for Bluno 2")                
                            count2 += 1
            except Exception as e:
                print(f"An error occurred: {e}")
                
                helloPacketReceived2 = False
                connPacketReceived2 = False
                break
                
def connectToBLE2():
    # Establish connection to Bluno2
    try:
        bluno = Peripheral(Bluno2_MAC_Address, "public")

        # Establish Delegate to handle notification
        bluno.setDelegate(SensorsDelegate2())
    
        # Retrieve Service and Characteristics
        svc = bluno.getServiceByUUID("dfb0")
        ch = svc.getCharacteristics("dfb1")[0]

    
        return (bluno, ch)
    except Exception as e:
        print("Unable to connect to Bluno 2...")

    return connectToBLE2()


def Bluno3():
    while True:
        global helloPacketReceived3
        global connPacketReceived3

        global ch3
        print("Connecting to device 3...")

        bluno, ch3 = connectToBLE3()
        print("Device connected 3")


        print("START Request Sent")
        ch3.write(CRC8Packet.pack_data(HelloPacket(HELLO_PACKET_ID)))
        while True:
            global count3
            try:
                while True:
                    if bluno.waitForNotifications(10): # calls handleNotification()
                        
                        
                        if ((helloPacketReceived3 == True) and (connPacketReceived3 == False)):
                            ch3.write(CRC8Packet.pack_data(HelloPacket(CONN_EST_PACKET_ID)))
                        
                        elif (helloPacketReceived3 and connPacketReceived3 and (count3 == 0)):
                            print("Connection Established for Bluno 3")                
                            count3 += 1
            except Exception as e:
                print(f"An error occurred: {e}")
                
                helloPacketReceived3 = False
                connPacketReceived3 = False
                break

def connectToBLE3():
    # Establish connection to Bluno3
    try:
        bluno = Peripheral(Bluno3_MAC_Address, "public")

        # Establish Delegate to handle notification
        bluno.setDelegate(SensorsDelegate3())
    
        # Retrieve Service and Characteristics
        svc = bluno.getServiceByUUID("dfb0")
        ch = svc.getCharacteristics("dfb1")[0]

    
        return (bluno, ch)
    except Exception as e:
        print("Unable to connect to Bluno 2...")

    return connectToBLE3()



# Sensor Delegate for Bluno 1
class SensorsDelegate1(DefaultDelegate):
    """
    Deleguate object from bluepy library to manage notifications from the Arduino Bluno through BLE.
    """
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data=0):
        """
        Sorts data transmitted by Arduino Bluno through BLE.
        """ 

        global helloPacketReceived1
        global connPacketReceived1
        global ch1

        if (cHandle==37):
            
            try:
                tuple_data = struct.unpack("BBHHHHHHHHBB", data)
                print(tuple_data)
                # print(tuple_data)
                checksum_value = CRC8Packet.calculate_crc8(data)
                if ((checksum_value == 0) and (tuple_data[1] == 0)):
                    if (helloPacketReceived1 == False):
                        print("Acknowledgement of HELLO PACKET Received from Bluno1")
                        helloPacketReceived1 = True
                    elif (connPacketReceived1 == False):
                        print("Acknowledgement of CONN EST Received from Bluno1")
                        connPacketReceived1 = True
                elif ((checksum_value == 0) and (tuple_data[1] == 4)):
                    # print(tuple_data)
                
                    ch1.write(CRC8Packet.pack_data(AckPacket(ACK_PACKET_ID)))
                else:
                    
                    print("NAK PACKET SENT")
                    ch1.write(CRC8Packet.pack_data(AckPacket(NAK_PACKET_ID)))
            except Exception as e:
                print("NAK PACKET SENT DUE TO EXCEPTION")
                ch1.write(CRC8Packet.pack_data(AckPacket(NAK_PACKET_ID)))
                            
# Sensor Delegate for Bluno 2
class SensorsDelegate2(DefaultDelegate):
    """
    Deleguate object from bluepy library to manage notifications from the Arduino Bluno through BLE.
    """
    def __init__(self):
        DefaultDelegate.__init__(self)
        

    def handleNotification(self, cHandle, data=0):
        """
        Sorts data transmitted by Arduino Bluno through BLE.
        """

        global helloPacketReceived2
        global connPacketReceived2
        global ch2

        if (cHandle==37):
            
            try:
                tuple_data = struct.unpack("BBHHHHHHHHBB", data)
                print(tuple_data)
                # print(tuple_data)
                checksum_value = CRC8Packet.calculate_crc8(data)
                if ((checksum_value == 0) and (tuple_data[1] == 0)):
                    if (helloPacketReceived2 == False):
                        print("Acknowledgement of HELLO PACKET Received from Bluno2")
                        helloPacketReceived2 = True
                    elif (connPacketReceived2 == False):
                        print("Acknowledgement of CONN EST Received from Bluno2")
                        connPacketReceived2 = True
                elif ((checksum_value == 0) and (tuple_data[1] == 4)):
                    # print(tuple_data)
                    ch2.write(CRC8Packet.pack_data(AckPacket(ACK_PACKET_ID)))
                else:
                    print("NAK PACKET SENT")
                    ch2.write(CRC8Packet.pack_data(AckPacket(NAK_PACKET_ID)))
            except Exception as e:
                print("NAK PACKET SENT DUE TO EXCEPTION")
                ch2.write(CRC8Packet.pack_data(AckPacket(NAK_PACKET_ID)))

# Sensor Delegate for Bluno 3
class SensorsDelegate3(DefaultDelegate):
    """
    Deleguate object from bluepy library to manage notifications from the Arduino Bluno through BLE.
    """
    def __init__(self):
        DefaultDelegate.__init__(self)
        

    def handleNotification(self, cHandle, data=0):
        """
        Sorts data transmitted by Arduino Bluno through BLE.
        """

        global helloPacketReceived3
        global connPacketReceived3
        global ch3

        if (cHandle==37):
            
            try:
                tuple_data = struct.unpack("BBHHHHHHHHBB", data)
                print(tuple_data)
                # print(tuple_data)
                checksum_value = CRC8Packet.calculate_crc8(data)
                if ((checksum_value == 0) and (tuple_data[1] == 0)):
                    if (helloPacketReceived3 == False):
                        print("Acknowledgement of HELLO PACKET Received from Bluno3")
                        helloPacketReceived3 = True
                    elif (connPacketReceived3 == False):
                        print("Acknowledgement of CONN EST Received from Bluno3")
                        connPacketReceived3 = True
                elif ((checksum_value == 0) and (tuple_data[1] == 4)):
                    # print(tuple_data)
                    ch3.write(CRC8Packet.pack_data(AckPacket(ACK_PACKET_ID)))
                else:
                    print("NAK PACKET SENT")
                    ch3.write(CRC8Packet.pack_data(AckPacket(NAK_PACKET_ID)))
            except Exception as e:
                print("NAK PACKET SENT DUE TO EXCEPTION")
                ch3.write(CRC8Packet.pack_data(AckPacket(NAK_PACKET_ID)))

# Declare Thread
t1 = threading.Thread(target=Bluno1)
t2 = threading.Thread(target=Bluno2)
t3 = threading.Thread(target=Bluno3)

# Main Function
if __name__=='__main__':
    t1.start()
    t2.start()    
    t3.start()
