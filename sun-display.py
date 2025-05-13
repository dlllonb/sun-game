# file for sun display

import serial
import time
import pygame
import os
import traceback
from collections import deque

# may not be COM6 depending on your system, must pair to device first
port = 'COM6'
try:
    bt = serial.Serial(port=port, baudrate=115200, timeout=1)
    time.sleep(1)  # Let the connection settle
    print(f"Connected to Serial on {port}")
except:
    print("Skipping Serial connection.")

pygame.init()
SCREEN_SIZE = 1000
screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
pygame.display.set_caption("Sun Simulation")
clock = pygame.time.Clock()
print("Set up PyGame.")
time.sleep(1)

# load in sun images
IMAGE_FOLDER = "sun-frames"
try:
        # Get a sorted list of filenames first
    image_files = sorted([
        f for f in os.listdir(IMAGE_FOLDER)
        if f.endswith('.png')
    ])

    # Then load the images
    sun_frames = [pygame.image.load(os.path.join(IMAGE_FOLDER, f)) for f in image_files]
    print(f"Loaded in {len(sun_frames)} sun frames")
except Exception as e:
    traceback.print_exc()
    input("Failed to load images...")


FPS = 60

running = True
frame_index = 0
rotation_speed = 0.1 # no lower than .2
rotation_speed_history = deque([rotation_speed])

x_drift = 0
y_drift = 0

def read_arduino_sensor_data(bt, num_parts):
    if bt and bt.in_waiting > 0:
        line = bt.readline().decode('utf-8', errors='ignore').strip()
        if line:
            parts = line.split()
            if len(parts) == num_parts:
                try:
                    return [float(x) for x in parts]
                except ValueError:
                    print(f"Malformed float in line: {line}")
    return [float(0) for _ in range(num_parts)]

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    sensor_data = read_arduino_sensor_data(bt, 3)
    sensor_rotation = sensor_data[2] / 2000
    sensor_drift_x = sensor_data[0] / 2000
    sensor_drift_y = sensor_data[1] / 2000

    # if -0.2 < sensor_rotation < 0.2:
    #     sensor_rotation = 0.2 if sensor_rotation > 0 else -0.2

    # LIVE ROTATION CHANGING
    rotation_speed_history.append(sensor_rotation)
    if len(rotation_speed_history) > 10:
        rotation_speed_history.popleft()
    rotation_speed = sum(rotation_speed_history) / len(rotation_speed_history)

    # LIVE TILT SHIFTING
    dx = sensor_drift_x
    dy = sensor_drift_y
    x_drift += dx - (x_drift / 100)
    y_drift += dy - (y_drift / 100)

    # Clear screen
    screen.fill((0, 0, 0))
    frame_base = int(frame_index) % len(sun_frames)
    frame_next = (frame_base + 1) % len(sun_frames)
    blend_ratio = frame_index - frame_base  # value between 0 and 1

    frame_surface = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE), pygame.SRCALPHA)

    x_offset = ((SCREEN_SIZE - 512) // 2) + x_drift
    y_offset = ((SCREEN_SIZE - 512) // 2) + y_drift
    alpha_next = int(blend_ratio * 255)
    alpha_base = 255 - alpha_next 
    sun_frames[frame_base].set_alpha(alpha_base)
    sun_frames[frame_next].set_alpha(alpha_next)
    frame_surface.blit(sun_frames[frame_base], (x_offset, y_offset))
    frame_surface.blit(sun_frames[frame_next], (x_offset, y_offset))
    sun_frames[frame_base].set_alpha(255)
    sun_frames[frame_next].set_alpha(255)

    screen.blit(frame_surface, (0, 0))
    #print(f"Showing frame {int(frame_index) % len(sun_frames)}")

    pygame.display.flip()
    frame_index += rotation_speed
    clock.tick(FPS)

pygame.quit()
