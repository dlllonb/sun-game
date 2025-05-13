# file for sun display

import serial
import time
import pygame
import os
import traceback

# may not be COM6 depending on your system, must pair to device first
port = 'COM6'
try:
    bt = serial.Serial(port=port, baudrate=115200, timeout=1)
    time.sleep(1)  # Let the connection settle
    print(f"Connected to Serial on {port}")
except:
    print("Skipping Serial connection.")

pygame.init()
screen = pygame.display.set_mode((800, 800))
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
rotation_speed = 0.25

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear screen
    screen.fill((0, 0, 0))

    # Show current frame
    frame = sun_frames[int(frame_index) % len(sun_frames)]
    print(f"Showing frame {int(frame_index) % len(sun_frames)}")
    rect = frame.get_rect(center=(400, 400))
    screen.blit(frame, rect)

    pygame.display.flip()

    # Advance frame index
    frame_index += rotation_speed

    clock.tick(FPS)

pygame.quit()
