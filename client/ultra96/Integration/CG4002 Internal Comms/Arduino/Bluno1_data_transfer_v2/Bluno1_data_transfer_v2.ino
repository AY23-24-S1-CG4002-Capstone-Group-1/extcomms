//#include "CRC8.h"
#include "CRC8.h"
#include "CRC.h"
#include "Bluno_Variables.h"

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
}


void loop() {
  struct Hello_Packet hello_packet_response;
  
  // Check for data available
  while (Serial.available()) {
    if (index != 20) {
      
      byte data = Serial.read();
      incomingData[index] = data;
      index += 1;
    } 
  }

 


  if (index == 20) {
    index = 0;

    if (calculateCRC8(incomingData, 20) == 0){
      
      // Sending Hello Packet
      if ((incomingData[PACKET_ID_INDEX] == HELLO_PACKET_ID) || (incomingData[PACKET_ID_INDEX] == CONN_EST_PACKET_ID)){
        // Hello Packet is correctly computed, hence write a response to send back to Relay Node.
        hello_packet_response = computeHelloPacketResponse();


        // If previous connected and Arduino is not powered off, then restart manually
        if ((hasReceivedHelloPacket == true) && (hasReceivedConnPacket)) {
          hasReceivedHelloPacket = false;
          hasReceivedConnPacket = false;
        }

        // Make sure the 2 handshake start
        if (hasReceivedHelloPacket == false) {
          Serial.write((uint8_t*) &hello_packet_response, sizeof(hello_packet_response));  
          hasReceivedHelloPacket = true;  
        } else if (hasReceivedConnPacket == false) {
          Serial.write((uint8_t*) &hello_packet_response, sizeof(hello_packet_response));  
          hasReceivedConnPacket = true;
          isReadyToSendData = true; 
        }
      } else if (incomingData[PACKET_ID_INDEX] == ACK_PACKET_ID) {
        
          isReadyToSendData = true;
      } else if (incomingData[PACKET_ID_INDEX] == NAK_PACKET_ID) {
          struct Data_Packet data_packet;
          data_packet = computeDataPacketResponse();
          Serial.write((uint8_t*) &data_packet, sizeof(data_packet));
      }

       
    }
  }

  // The part on sending data
  if (isReadyToSendData) {
    struct Data_Packet data_packet;
    data_packet = computeDataPacketResponse();
    Serial.write((uint8_t*) &data_packet, sizeof(data_packet));
    isReadyToSendData = false;
  }
  
  
  
}
    
    

      
    
      
   
