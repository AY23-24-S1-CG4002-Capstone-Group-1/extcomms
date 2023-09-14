#ifndef BLUNO_VARIABLES_3_H
#define BLUNO_VARIABLES_3_H

#include <Arduino.h>
#include "CRC8.h"
#include "CRC.h"

extern byte incomingData[20];
extern int index;

const int RELAY_NODE_DEVICE_ID = 0;
const int BLUNO_1_DEVICE_ID = 1;
const int BLUNO_2_DEVICE_ID = 2;
const int BLUNO_3_DEVICE_ID = 3;

const int HELLO_PACKET_ID = 0;
const int CONN_EST_PACKET_ID = 1;
const int ACK_PACKET_ID = 2;
const int NAK_PACKET_ID = 3;
const int DATA_PACKET_ID = 4;

const int PACKET_ID_INDEX = 1;

extern bool hasReceivedHelloPacket;
extern bool hasReceivedConnPacket;
extern bool isReadyToSendData;


struct Hello_Packet {
  uint8_t Device_ID;
  uint8_t Packet_ID;
    
  uint16_t Padding_1;
  uint16_t Padding_2;
  uint16_t Padding_3;
  uint16_t Padding_4;
  uint16_t Padding_5;
  uint16_t Padding_6;
  uint16_t Padding_7;
  uint16_t Padding_8;
  uint8_t Padding_9;

  uint8_t Checksum;
};

struct Data_Packet {
  uint8_t Device_ID;
  uint8_t Packet_ID;

  uint16_t IRReceiver;
  uint16_t Padding_1;
  uint16_t Padding_2;
  uint16_t Padding_3;

  uint16_t Padding_4;
  uint16_t Padding_5;
  uint16_t Padding_6;

  uint16_t Padding_7;
  uint8_t Padding_8;

  uint8_t Checksum;
};

uint8_t calculateCRC8(void* hello_packet, int packet_length);
Hello_Packet computeHelloPacketResponse();
Data_Packet computeDataPacketResponse();

#endif
