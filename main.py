# main file that does the control loop reading and writing 
import serial
import time
import pygame
import sys
import math

# set up serial connection
arduino = serial.Serial(port='COM3', baudrate=115200, timeout=1)
time.sleep(0.5)
print('Starting...')

latest_data = None

def send_command(command):
    if arduino and arduino.is_open:
        arduino.write((command.strip() + '\n').encode('utf-8'))

while True:
    if arduino.in_waiting > 0:
        line = arduino.readline().decode('utf-8', errors='ignore').strip()
        if line:
            parts = line.split()
            if len(parts) == 7:
                try:
                    latest_data = [float(x) for x in parts]
                except ValueError:
                    print(f"Malformed float in line: {line}")

    # time.sleep can be adjusted as needed
    time.sleep(0.01)
