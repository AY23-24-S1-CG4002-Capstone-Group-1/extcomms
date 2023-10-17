import os, warnings
from pynq import PL
from pynq import Overlay
from pynq import allocate 
import numpy as np

def predict_action(readings):
    actions_bit = "action.bit"
    ol = Overlay(actions_bit)

    dma = ol.axi_dma_0
    dma_send = dma.sendchannel
    dma_recv = dma.recvchannel

    ip = ol.example_1

    #start the ip
    CONTROL_REGISTER = 0x0
    ip.write(CONTROL_REGISTER, 0x81)

    data_size = 32*8

    input_buffer = allocate(shape=(data_size,), dtype=np.uint32)
    output_buffer = allocate(shape=(1,), dtype=np.uint32)

    for i in range(len(readings)):
        input_buffer[i] = readings[i]
    
    dma_send.transfer(input_buffer)
    dma_send.wait()
    dma_recv.transfer(output_buffer)

    action = output_buffer[0]

    del input_buffer, output_buffer

    return action


# readings = [0]*(32*8)
# for i in range (32*8): 
#     readings[i] = i+4

# print(predict_action(readings))

    
