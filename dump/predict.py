import os, warnings
from pynq import PL
from pynq import Overlay
from pynq import allocate 
from random import randint

import numpy as np
from numpy.fft import fft, ifft

from standardisation import means
from standardisation import stds


def fft_funct(x, n): 
    Ts = 0.05
    Sr = 1/Ts
    
    t = np.arange(0,(n)*Ts, Ts)
    
    X = fft(x)
    N = len(X)
    
    n = np.arange(N)
    T = N/Sr
    freq = n/T
    
    return np.abs(X)

def preprocess(readings):
    count = 0
    num_sensors = 8 
    num_samples = 30
    frac_bits = 16
    
    sequences = np.zeros((num_sensors, num_samples))
    data = []
    
    for j in range(num_sensors):
        data.extend(sequences[j])
        if j >= 6:
            continue
        data.extend(fft_funct(sequences[j], num_samples))    
    
    #standardise
    for i in range(14*30):
        data[i] = int(((data[i] - means[i])/stds[i])*(2**frac_bits))
        
    return data

def predict_action(readings):
    actions_bit = "design_1_wrapper.bit"
    ol = Overlay(actions_bit)

    #read in the data in the right order
    for i in range(int(len(readings) / 8)):
        for j in range(8):
            if (j == 0 or j == 1 or j == 2): 
                k = readings[i*8 + j + 3]
                readings[i*8 + j + 3] = readings[i*8 + j]
                readings[i*8 + j] = k


    dma = ol.axi_dma_0
    dma_send = dma.sendchannel
    dma_recv = dma.recvchannel

    ip = ol.model_1

    #start the ip
    CONTROL_REGISTER = 0x0
    ip.write(CONTROL_REGISTER, 0x81)
#    dma.register_map.MM2S_DMACR.Reset = 1

    data_size = 14*30

    input_buffer = allocate(shape=(data_size,), dtype=np.int32)
    output_buffer = allocate(shape=(1,), dtype=np.uint32)

    readings = preprocess(readings)

    for i in range(data_size):
        input_buffer[i] = readings[i]
    
    dma_send.transfer(input_buffer)
    dma_send.wait()
    dma_recv.transfer(output_buffer)

    action = output_buffer[0]

    del input_buffer, output_buffer

    return action


readings = [0]*(32*8)

for i in range(15):
    for i in range (32*8): 
        readings[i] = randint(0,256)

    print(predict_action(readings))
