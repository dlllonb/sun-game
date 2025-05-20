import serial
import time
import pygame
import os
import traceback
from collections import deque
import math
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Sun Simulation Game")
parser.add_argument('--rotation', type=float, default=None, help='Constant sun spin rate (disables Arduino)')
args = parser.parse_args()

if args.rotation is None:
    # Mac, something like:
    port = '/dev/tty.ESP32Sun'
    # PC 
    # may not be COM6 depending on your system, must pair to device first
    # port = 'COM6'
    try:
        bt = serial.Serial(port=port, baudrate=115200, timeout=1)
        time.sleep(1)  # Let the connection settle
        print(f"Connected to Serial on {port}")
    except Exception as e:
        print(f"Skipping Serial connection: {e}")
else:
    bt = None

pygame.init()
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 1000
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Sun Simulation")
clock = pygame.time.Clock()
print("Set up PyGame.")
time.sleep(1)

# load in sun images
IMAGE_FOLDER = "sun-frames-background-removed"
SUN_SIZE = 275
try:
        # Get a sorted list of filenames first
    image_files = sorted([
        f for f in os.listdir(IMAGE_FOLDER)
        if f.endswith('.png')
    ])

    # Then load the images
    sun_frames = [pygame.image.load(os.path.join(IMAGE_FOLDER, f)) for f in image_files]
    sun_frames = [pygame.transform.smoothscale(img, (SUN_SIZE, SUN_SIZE)) for img in sun_frames]
    print(f"Loaded in {len(sun_frames)} sun frames")
except Exception as e:
    traceback.print_exc()
    input("Failed to load images...")


FPS = 60

running = True
frame_index = 0
if args.rotation is not None:
    rotation_speed = args.rotation
    rotation_speed_history = deque([rotation_speed])
else:
    rotation_speed = 0.1 # no lower than .2
    rotation_speed_history = deque([rotation_speed])

x_drift = 0
y_drift = 0

# Earth orbit parameters
ORBIT_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)
ORBIT_A = 600  # major axis
ORBIT_B = 140  # minor axis (for tilt)

orbit_distance = 0  # vertical offset from the sun, can be 0 for now
orbit_tilt_degree = 0  # degrees, 0 = horizontal, positive = counterclockwise tilt

earth_angle = 0  # initial angle
EARTH_ORBIT_SPEED = 0.01  # base speed, can be affected by instability

# Stability thresholds
ROTATION_MIN = 0
ROTATION_MAX = 2
DRIFT_MAX = 40

instability_counter = 0
INSTABILITY_LIMIT = 180  # frames (3 seconds at 60 FPS)
game_over = False

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

def get_earth_pos(angle, tilt_deg=orbit_tilt_degree, distance=orbit_distance):
    # Convert tilt to radians
    tilt = math.radians(tilt_deg)
    # Parametric ellipse
    x = ORBIT_A * math.cos(angle)
    y = ORBIT_B * math.sin(angle)
    # Apply tilt (rotation matrix)
    x_tilt = x * math.cos(tilt) - y * math.sin(tilt)
    y_tilt = x * math.sin(tilt) + y * math.cos(tilt)
    # Apply distance (vertical offset)
    return (ORBIT_CENTER[0] + x_tilt, ORBIT_CENTER[1] + y_tilt + distance)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if not game_over:
        if args.rotation is not None:
            # Use constant rotation speed, no Arduino
            pass  # rotation_speed is already set, no drift
        else:
            sensor_data = read_arduino_sensor_data(bt, 3)
            sensor_rotation = sensor_data[2] / 2000
            sensor_drift_x = sensor_data[0] / 2000
            sensor_drift_y = sensor_data[1] / 2000

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

        # --- Stability Check ---
        unstable = (
            rotation_speed < ROTATION_MIN or
            rotation_speed > ROTATION_MAX or
            abs(x_drift) > DRIFT_MAX or
            abs(y_drift) > DRIFT_MAX
        )
        if unstable:
            instability_counter += 1
        else:
            instability_counter = max(0, instability_counter - 1)

        if instability_counter > INSTABILITY_LIMIT:
            game_over = True

        # --- Earth Orbit ---
        # Earth orbits faster if unstable
        earth_angle -= EARTH_ORBIT_SPEED + (0.01 if unstable else 0)
        if earth_angle > 2 * math.pi:
            earth_angle -= 2 * math.pi

    # --- Drawing ---
    screen.fill((0, 0, 0))

    # Draw orbit ellipse (for reference, optional)
    pygame.draw.ellipse(
        screen, (50, 50, 100), 
        [ORBIT_CENTER[0] - ORBIT_A, ORBIT_CENTER[1] - ORBIT_B, ORBIT_A * 2, ORBIT_B * 2], 1
    )

    # Calculate Earth position
    earth_pos = get_earth_pos(earth_angle, orbit_tilt_degree, orbit_distance)
    # Earth is behind if its y-position is greater than the center (i.e., visually lower)
    earth_behind = get_earth_pos(earth_angle)[1] < ORBIT_CENTER[1]

    # --- Sun Drawing (existing code) ---
    frame_base = int(frame_index) % len(sun_frames)
    frame_next = (frame_base + 1) % len(sun_frames)
    blend_ratio = frame_index - frame_base  # value between 0 and 1

    frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    # Draw Earth behind sun if needed (drawn on frame_surface)
    if earth_behind:
        pygame.draw.circle(frame_surface, (80, 120, 255), (int(earth_pos[0]), int(earth_pos[1])), 32)

    x_offset = ((SCREEN_WIDTH - SUN_SIZE) // 2) + x_drift
    y_offset = ((SCREEN_HEIGHT - SUN_SIZE) // 2) + y_drift
    alpha_next = int(blend_ratio * 255)
    alpha_base = 255 - alpha_next 

    # Make copies before setting alpha
    base_img = sun_frames[frame_base].copy()
    next_img = sun_frames[frame_next].copy()
    base_img.set_alpha(alpha_base)
    next_img.set_alpha(alpha_next)
    frame_surface.blit(base_img, (x_offset, y_offset))
    frame_surface.blit(next_img, (x_offset, y_offset))

    # Blit the combined frame to the screen
    screen.blit(frame_surface, (0, 0))

    # Draw Earth in front if needed (drawn on screen)
    if not earth_behind:
        pygame.draw.circle(screen, (80, 120, 255), (int(earth_pos[0]), int(earth_pos[1])), 32)

    # --- Game Over Message ---
    if game_over:
        font = pygame.font.SysFont(None, 80)
        text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
        font2 = pygame.font.SysFont(None, 40)
        text2 = font2.render("Earth's orbit destabilized!", True, (255, 255, 255))
        screen.blit(text2, (SCREEN_WIDTH // 2 - text2.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

    pygame.display.flip()
    if not game_over:
        frame_index += rotation_speed
    clock.tick(FPS)

pygame.quit()
