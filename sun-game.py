import serial
import time
import pygame
import os
import traceback
from collections import deque
import math
import argparse
import random
from explosion import ExplosionSystem

# Game States
STATE_TITLE = 0
STATE_SUN_RISING = 1
STATE_EARTH_INTRO = 3
STATE_GAME_PLAY = 4
STATE_GAME_OVER = 5

class GameState:
    def __init__(self):
        self.current_state = STATE_TITLE
        self.explosion = None
        
    def start_explosion(self, x, y, sun_frame):
        self.explosion = ExplosionSystem(x, y, sun_frame)
        
    def reset_explosion(self):
        self.explosion = None

# Animation timing constants (in milliseconds)
RISING_TEXT_DURATION = 18000  # Time for text to rise
RISING_SUN_DURATION = 8000   # Time for sun to rise and reach full spin
FINAL_RISING_PAUSE = 2000    # Brief pause at full spin before Earth intro

# Target spin speed for stable spinning
TARGET_SPIN_SPEED = 0.8

ZOOM_IN_DURATION = 2000     # Time to zoom into side position
EARTH_FADE_DURATION = 2000   # Time for Earth to fade in
EARTH_MOVE_DURATION = 3000   # Time for Earth to start moving
ZOOM_OUT_DURATION = 3000     # Time to zoom out to full view

EARTH_APPEAR_DURATION = 2000  # Time for Earth to fade in
EARTH_ZOOM_DURATION = 4000    # Time for Earth to zoom to position
EARTH_ORBIT_START_DURATION = 3000  # Time to start orbital motion


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Sun Simulation Game")
parser.add_argument('--rotation', type=float, default=None, help='Constant sun spin rate (disables Arduino)')
args = parser.parse_args()

if args.rotation is None:
    # Mac, something like:
    # port = '/dev/tty.ESP32Sun'
    # PC 
    # may not be COM6 depending on your system, must pair to device first
    port = 'COM6'
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

    # Load Earth image
    EARTH_DISPLAY_SIZE = 64  # Size for display
    EARTH_LOAD_SIZE = 512    # Size to load at (higher resolution)
    earth_img = pygame.image.load('earth_default.png')
    # First scale to high resolution
    earth_img = pygame.transform.smoothscale(earth_img, (EARTH_LOAD_SIZE, EARTH_LOAD_SIZE))
    # Then create display version
    earth_display_img = pygame.transform.smoothscale(earth_img, (EARTH_DISPLAY_SIZE, EARTH_DISPLAY_SIZE))
    print("Loaded Earth image")
except Exception as e:
    traceback.print_exc()
    input("Failed to load images...")

# Earth appearance states
EARTH_STATES = {
    0: earth_display_img,    # Default blue
    1: earth_display_img,   # More green
    2: earth_display_img,   # Yellow-ish
    3: earth_display_img,   # Reddish
    4: earth_display_img,     # Dark red
}
EARTH_STATE_DURATION = 30000  # Duration for each Earth in milliseconds (30 seconds)
current_earth_state = 0
earth_state_start_time = 0

FPS = 60

running = True
frame_index = 0
if args.rotation is not None:
    rotation_speed = args.rotation
    rotation_speed_history = deque([rotation_speed])
else:
    rotation_speed = 0.2
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
ROTATION_MIN = 0.3
ROTATION_MAX = 1.5
DRIFT_MAX = 20
DRIFT_SUPER_MAX = 50

instability_counter = 0
INSTABILITY_LIMIT = 100
# game_over = False # Replaced by game_state
current_game_state = STATE_TITLE # Initial game state

years = 0.0
displayed_year = 0
prev_earth_angle = earth_angle
YEARS_PER_ORBIT = 100

# After pygame.init() and before the main loop
rising_start_time = 0  # Will be set when STATE_SUN_RISING begins
rising_phase = 0       # 0: text rising, 1: pause, 2: sun rising, 3: complete

spinning_start_time = 0
spinning_phase = 0  # 0: accelerating, 1: stable spinning, 2: showing prompt

earth_intro_start_time = 0
earth_intro_phase = 0  # 0: zooming in, 1: earth appearing, 2: earth moving, 3: zooming out

def reset_rising_animation():
    global rising_start_time, rising_phase
    rising_start_time = pygame.time.get_ticks()
    rising_phase = 0

def reset_spinning_animation():
    global spinning_start_time, spinning_phase, frame_index
    spinning_start_time = pygame.time.get_ticks()
    spinning_phase = 0
    frame_index = 0  # Reset sun animation frame

def reset_earth_intro_animation():
    global earth_intro_start_time, earth_intro_phase
    earth_intro_start_time = pygame.time.get_ticks()
    earth_intro_phase = 0

def get_earth_appearance(current_time):
    global current_earth_state, earth_state_start_time
    
    # Initialize start time if not set
    if earth_state_start_time == 0:
        earth_state_start_time = current_time
    
    # Check if it's time to change state
    elapsed = current_time - earth_state_start_time
    if elapsed >= EARTH_STATE_DURATION:
        # Move to next state
        current_earth_state = (current_earth_state + 1) % len(EARTH_STATES)
        earth_state_start_time = current_time
    
    return EARTH_STATES[current_earth_state]

# Initialize rising animation when game starts
reset_rising_animation()

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

# Initialize game state
game_state = GameState()
current_game_state = STATE_TITLE  # For compatibility with existing code

while running:
    events = pygame.event.get() # Get events once per frame
    current_time = pygame.time.get_ticks()
    
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        
        # Handle state-specific KEYDOWN events for transitions or actions
        if game_state.current_state == STATE_TITLE:
            if event.type == pygame.KEYDOWN:
                game_state.current_state = STATE_SUN_RISING
                reset_rising_animation()  # Start animation timing
        elif game_state.current_state == STATE_SUN_RISING:
            # Animation will control state transition now
            pass
        elif game_state.current_state == STATE_EARTH_INTRO:
            if event.type == pygame.KEYDOWN and event.key == pygame.KEYDOWN:
                game_state.current_state = STATE_GAME_PLAY
        elif game_state.current_state == STATE_GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                # Reset all game state variables
                frame_index = 0
                if args.rotation is not None:
                    rotation_speed = args.rotation
                    rotation_speed_history = deque([rotation_speed])
                else:
                    rotation_speed = 0.2
                    rotation_speed_history = deque([rotation_speed])
                x_drift = 0
                y_drift = 0
                current_earth_state = 0
                earth_state_start_time = 0
                orbit_distance = 0
                orbit_tilt_degree = 0
                earth_angle = 0
                prev_earth_angle = earth_angle
                instability_counter = 0
                game_state.current_state = STATE_GAME_PLAY
                game_state.reset_explosion()
                years = 0.0
                displayed_year = 0
            if event.type == pygame.KEYDOWN and event.key == pygame.K_x:
                game_state.current_state == STATE_TITLE
                # Reset all game state variables
                frame_index = 0
                if args.rotation is not None:
                    rotation_speed = args.rotation
                    rotation_speed_history = deque([rotation_speed])
                else:
                    rotation_speed = 0.2
                    rotation_speed_history = deque([rotation_speed])
                x_drift = 0
                y_drift = 0
                current_earth_state = 0
                earth_state_start_time = 0
                orbit_distance = 0
                orbit_tilt_degree = 0
                earth_angle = 0
                prev_earth_angle = earth_angle
                instability_counter = 0
                game_state.current_state = STATE_GAME_PLAY
                game_state.reset_explosion()
                years = 0.0
                displayed_year = 0

    screen.fill((0, 0, 0)) # Clear screen once at the beginning of the loop

    if game_state.current_state == STATE_TITLE:
        # Only show title screen elements, no game objects
        screen.fill((0, 0, 0))  # Clear screen with black
        font = pygame.font.SysFont(None, 100)
        title_text = font.render("HELIOS", True, (255, 255, 255))
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
        font_small = pygame.font.SysFont(None, 36)
        prompt_text = font_small.render("Press any key to start", True, (200, 200, 200))
        screen.blit(prompt_text, (SCREEN_WIDTH // 2 - prompt_text.get_width() // 2, SCREEN_HEIGHT // 2))
        pygame.display.flip()  # Update the display
        continue  # Skip the rest of the loop to avoid drawing game objects

    # Update current_game_state for compatibility with existing code
    current_game_state = game_state.current_state

    if game_state.current_state == STATE_SUN_RISING:
        elapsed = current_time - rising_start_time
        
        if rising_phase == 0:  # Text rising phase
            if elapsed < RISING_TEXT_DURATION:
                # Calculate text position (move from bottom to top)
                progress = elapsed / RISING_TEXT_DURATION
                
                font = pygame.font.SysFont(None, 50)
                texts = [
                    "Since ancient times, cultures around the world have had Sun gods.",
                    "Apollo. Ra. Sol Invictus. Helios.",
                    "And now you. ",
                    "",
                    "",
                    "Imagine you now hold the power of the Sun",
                    "in the palm of your hand—because you do.",
                    "",
                    "",
                    "A flick of your wrist",
                    "and all life on Earth is gone,",
                    "along with the rest of the solar system,",
                    "in a single flash of sunlight.",
                    "",
                    "",
                    "The power of a billions of ",
                    "thermonuclear bombs every single second,",
                    "and stability relies on you.",
                    "",
                    "",
                    "Keep the Sun spinning and stable. ",
                    "Or don't. ",
                    "You're the sun god. "
                ]
                
                # Calculate total height needed for all text
                LINE_SPACING = 60
                total_text_height = len(texts) * LINE_SPACING
                # Add extra padding to ensure all text moves off screen
                total_distance = SCREEN_HEIGHT + total_text_height + 100  # 100px extra padding
                
                # Calculate starting Y position that will allow all text to be visible
                start_y = SCREEN_HEIGHT + LINE_SPACING
                # Calculate current Y position
                text_y = start_y - (progress * total_distance)
                
                # Draw each line of text with spacing
                for i, line in enumerate(texts):
                    text_surface = font.render(line, True, (255, 255, 255))
                    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH/2, text_y + i*LINE_SPACING))
                    # Only draw text if it's in or near the visible area
                    if -100 <= text_rect.bottom <= SCREEN_HEIGHT + 100:
                        screen.blit(text_surface, text_rect)
            else:
                rising_phase = 1
                rising_start_time = current_time  # Reset timer for sun rising phase
        
        elif rising_phase == 1:  # Combined sun rising and spinning phase
            if elapsed < RISING_SUN_DURATION:
                progress = elapsed / RISING_SUN_DURATION

                # Use ease-out for position
                position_progress = 1 - (1 - progress) * (1 - progress)
                
                # Calculate sun position (move from below screen to center)
                sun_y = SCREEN_HEIGHT + SUN_SIZE//2 - (position_progress * ((SCREEN_HEIGHT + SUN_SIZE//2) - SCREEN_HEIGHT//2))
                
                current_spin_speed = min(TARGET_SPIN_SPEED, max(TARGET_SPIN_SPEED * progress, 0.25))
            
                # Update frame index for spinning
                frame_index += current_spin_speed
                frame_base = int(frame_index) % len(sun_frames)
                
                # Draw the sun at its current position
                frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                x_offset = (SCREEN_WIDTH - SUN_SIZE) // 2
                y_offset = int(sun_y - SUN_SIZE//2)
                frame_surface.blit(sun_frames[frame_base], (x_offset, y_offset))
                screen.blit(frame_surface, (0, 0))
            else:
                # Brief pause at full spin
                if elapsed < RISING_SUN_DURATION + FINAL_RISING_PAUSE:
                    frame_index += TARGET_SPIN_SPEED
                    frame_base = int(frame_index) % len(sun_frames)
                    
                    # Draw the sun at center
                    frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    x_offset = (SCREEN_WIDTH - SUN_SIZE) // 2
                    y_offset = (SCREEN_HEIGHT - SUN_SIZE) // 2
                    frame_surface.blit(sun_frames[frame_base], (x_offset, y_offset))
                    screen.blit(frame_surface, (0, 0))
                else:
                    # Transition directly to Earth intro
                    game_state.current_state = STATE_EARTH_INTRO
                    reset_earth_intro_animation()

    elif game_state.current_state == STATE_EARTH_INTRO:
        elapsed = current_time - earth_intro_start_time
        
        # Start Earth at -45 degrees (closer to center) instead of 0 degrees (far right of orbit)
        EARTH_START_ANGLE = -math.pi/4  # -45 degrees
        ORBIT_MOVEMENT_AMOUNT = math.pi/2  # How far the Earth moves during zoom out
        
        # Get Earth's orbital position - this is where we want to center the zoom
        earth_orbital_pos = get_earth_pos(EARTH_START_ANGLE)
        FINAL_ZOOM_CENTER_X = earth_orbital_pos[0]
        FINAL_ZOOM_CENTER_Y = earth_orbital_pos[1]
        MAX_ZOOM = 4.0
        
        # Start from the sun's center position
        START_CENTER_X = SCREEN_WIDTH / 2
        START_CENTER_Y = SCREEN_HEIGHT / 2
        
        # Draw base scene with sun (always in the same position as spinning stage)
        frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        x_offset = (SCREEN_WIDTH - SUN_SIZE) // 2
        y_offset = (SCREEN_HEIGHT - SUN_SIZE) // 2
        frame_index += TARGET_SPIN_SPEED
        frame_base = int(frame_index) % len(sun_frames)
        frame_surface.blit(sun_frames[frame_base], (x_offset, y_offset))
        
        if earth_intro_phase == 0:  # Zooming in phase
            if elapsed < ZOOM_IN_DURATION:
                progress = elapsed / ZOOM_IN_DURATION
                # Use ease-in-out for smooth zoom and movement
                ease_progress = progress * progress * (3 - 2 * progress)
                
                # Gradually move the view center from sun to Earth's position
                current_center_x = START_CENTER_X + (FINAL_ZOOM_CENTER_X - START_CENTER_X) * ease_progress
                current_center_y = START_CENTER_Y + (FINAL_ZOOM_CENTER_Y - START_CENTER_Y) * ease_progress
                
                # Calculate zoom scale with a slight delay to start
                zoom_progress = max(0, (progress - 0.1) * 1.1)  # Delay zoom start by 10%
                zoom_progress = min(1, zoom_progress)  # Clamp to 1
                zoom_scale = 1 + ((MAX_ZOOM - 1) * (zoom_progress * zoom_progress))  # Ease-in zoom
                
                # Calculate view offset based on current center
                view_offset_x = (current_center_x - SCREEN_WIDTH/2)
                view_offset_y = (current_center_y - SCREEN_HEIGHT/2)
            else:
                earth_intro_phase = 1
                earth_intro_start_time = current_time
                zoom_scale = MAX_ZOOM
                view_offset_x = (FINAL_ZOOM_CENTER_X - SCREEN_WIDTH/2)
                view_offset_y = (FINAL_ZOOM_CENTER_Y - SCREEN_HEIGHT/2)
        
        elif earth_intro_phase == 1:  # Earth appearing phase
            zoom_scale = MAX_ZOOM
            if elapsed < EARTH_FADE_DURATION:
                progress = elapsed / EARTH_FADE_DURATION
                # Use ease-in for smooth fade
                alpha = int(255 * (progress * progress))
                
                # Calculate size based on zoom
                zoomed_size = int(EARTH_DISPLAY_SIZE * zoom_scale)
                
                # Draw Earth with fade effect at its orbital position using high-res version
                earth_surface = pygame.Surface((EARTH_LOAD_SIZE, EARTH_LOAD_SIZE), pygame.SRCALPHA)
                # Create a copy of the high-res earth image and set its alpha
                temp_earth = earth_img.copy()
                temp_earth.set_alpha(alpha)
                earth_surface.blit(temp_earth, (0, 0))
                
                # Scale from high-res to zoomed size (maintaining quality)
                scaled_earth = pygame.transform.smoothscale(earth_surface, (zoomed_size, zoomed_size))
                earth_rect = scaled_earth.get_rect(center=earth_orbital_pos)
                frame_surface.blit(scaled_earth, earth_rect)
                
                view_offset_x = (FINAL_ZOOM_CENTER_X - SCREEN_WIDTH/2)
                view_offset_y = (FINAL_ZOOM_CENTER_Y - SCREEN_HEIGHT/2)
            else:
                earth_intro_phase = 2
                earth_intro_start_time = current_time
        
        elif earth_intro_phase == 2:  # Zooming out phase
            if elapsed < ZOOM_OUT_DURATION:
                progress = elapsed / ZOOM_OUT_DURATION
                # Use ease-in-out for smooth zoom
                ease_progress = progress * progress * (3 - 2 * progress)
                zoom_scale = MAX_ZOOM - ((MAX_ZOOM - 1) * ease_progress)
                
                # Calculate Earth's current angle with eased movement
                # Start movement slowly and then accelerate
                movement_progress = progress * progress  # Ease-in for orbital movement
                current_angle = EARTH_START_ANGLE - (ORBIT_MOVEMENT_AMOUNT * movement_progress)
                current_earth_pos = get_earth_pos(current_angle)

                zoomed_size = int(EARTH_DISPLAY_SIZE * zoom_scale)
                # Create scaled earth from high-res version
                scaled_earth = pygame.transform.smoothscale(earth_img, (zoomed_size, zoomed_size))
                
                # Check if Earth is behind sun for proper z-ordering
                earth_behind = current_earth_pos[1] < ORBIT_CENTER[1]
                
                # Draw Earth behind sun if needed
                if earth_behind:
                    earth_rect = scaled_earth.get_rect()
                    earth_rect.center = (int(current_earth_pos[0]), int(current_earth_pos[1]))
                    frame_surface.blit(scaled_earth, earth_rect)
                
                # Draw sun
                frame_surface.blit(sun_frames[frame_base], (x_offset, y_offset))
                
                # Draw Earth in front if needed
                if not earth_behind:
                    earth_rect = scaled_earth.get_rect()
                    earth_rect.center = (int(current_earth_pos[0]), int(current_earth_pos[1]))
                    screen.blit(scaled_earth, earth_rect)
                
                # Calculate view offset with transition back to center
                # Follow Earth's movement partially during first half of zoom out
                if progress < 0.5:
                    # Gradually reduce how much we follow the Earth
                    follow_strength = 1 - (progress * 2)  # Goes from 1 to 0 over first half
                    current_center_x = FINAL_ZOOM_CENTER_X + (current_earth_pos[0] - earth_orbital_pos[0]) * follow_strength
                    current_center_y = FINAL_ZOOM_CENTER_Y + (current_earth_pos[1] - earth_orbital_pos[1]) * follow_strength
                    view_offset_x = (current_center_x - SCREEN_WIDTH/2) * (1 - ease_progress)
                    view_offset_y = (current_center_y - SCREEN_HEIGHT/2) * (1 - ease_progress)
                else:
                    # Standard center transition for second half
                    view_offset_x = (FINAL_ZOOM_CENTER_X - SCREEN_WIDTH/2) * (1 - ease_progress)
                    view_offset_y = (FINAL_ZOOM_CENTER_Y - SCREEN_HEIGHT/2) * (1 - ease_progress)
            else:
                # Initialize gameplay variables with the exact final animation state
                earth_angle = current_angle  # Start gameplay at the final animation angle
                # Calculate initial movement speed based on the animation's final velocity
                # This helps match the gameplay movement to the animation end state
                EARTH_ORBIT_SPEED = (ORBIT_MOVEMENT_AMOUNT / ZOOM_OUT_DURATION) * 16.67  # Convert to per-frame speed
                # Initialize rotation speed to match the animation
                if args.rotation is None:
                    rotation_speed = TARGET_SPIN_SPEED
                    rotation_speed_history = deque([rotation_speed] * 10)  # Fill history with current speed
                game_state.current_state = STATE_GAME_PLAY
                # Don't reset frame_index here - let it continue from current value
        
        # Scale and position the view (consistent across all phases)
        scaled_surface = pygame.transform.scale(
            frame_surface,
            (int(SCREEN_WIDTH * zoom_scale), int(SCREEN_HEIGHT * zoom_scale))
        )
        screen.blit(
            scaled_surface,
            (-view_offset_x * zoom_scale - (SCREEN_WIDTH * (zoom_scale - 1))/2,
             -view_offset_y * zoom_scale - (SCREEN_HEIGHT * (zoom_scale - 1))/2)
        )

    elif game_state.current_state == STATE_GAME_PLAY:
        # --- Existing Game Logic ---
        if args.rotation is not None:
            # Use constant rotation speed, no Arduino
            frame_index += rotation_speed  # Make sure we're still updating frame_index
            pass  # rotation_speed is already set, no drift
        else:
            sensor_data = read_arduino_sensor_data(bt, 3)
            sensor_rotation = sensor_data[2] / 2500
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

            # Have tilt influence the orbit
            orbit_tilt_degree = max(-45, min(45, 0.1 * x_drift))

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

        if instability_counter > INSTABILITY_LIMIT or abs(x_drift) > DRIFT_SUPER_MAX or abs(y_drift) > DRIFT_SUPER_MAX:
            game_state.current_state = STATE_GAME_OVER

        # --- Earth Orbit ---
        prev_earth_angle = earth_angle  # Store previous angle
        earth_angle -= EARTH_ORBIT_SPEED # + (0.01 if unstable else 0)
        delta_angle = prev_earth_angle - earth_angle
        if delta_angle < 0:
            delta_angle += 2 * math.pi

        years += (delta_angle / (2 * math.pi)) * YEARS_PER_ORBIT

        if int(years) > displayed_year:
            displayed_year = int(years)

        if earth_angle < 0:
            earth_angle += 2 * math.pi

        # Draw base scene
        frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Calculate Earth position and z-order
        earth_pos = get_earth_pos(earth_angle, orbit_tilt_degree, orbit_distance)
        earth_behind = earth_pos[1] < ORBIT_CENTER[1]

        # Get current Earth appearance
        # earth_color = get_earth_appearance(current_time)

        # Draw Earth behind sun if needed
        if earth_behind:
            earth_rect = earth_display_img.get_rect()
            earth_rect.center = (int(earth_pos[0]), int(earth_pos[1]))
            frame_surface.blit(earth_display_img, earth_rect)

        # Draw sun
        x_offset = ((SCREEN_WIDTH - SUN_SIZE) // 2) + x_drift
        y_offset = ((SCREEN_HEIGHT - SUN_SIZE) // 2) + y_drift
        frame_base = int(frame_index) % len(sun_frames)
        frame_next = (frame_base + 1) % len(sun_frames)
        next_img = sun_frames[frame_next]
        frame_surface.blit(next_img, (x_offset, y_offset))
        
        # brightness = rotation_speed + instability between 0 and 1
        brightness = ((rotation_speed - ROTATION_MIN) / (ROTATION_MAX - ROTATION_MIN)) / 2  + \
                        ((instability_counter / INSTABILITY_LIMIT) / 2)

        # Set the maximum brighten value 
        max_brighten = 60
        brighten = int(brightness * max_brighten)

        if brighten > 0:
            circle_overlay = pygame.Surface((SUN_SIZE, SUN_SIZE))
            circle_overlay.set_colorkey((0, 0, 0))  # Make black transparent
            pygame.draw.circle(
                circle_overlay,
                (brighten, brighten, brighten),  # Pure white, but low value for subtlety
                (SUN_SIZE // 2, SUN_SIZE // 2),
                110
            )
            frame_surface.blit(circle_overlay, (x_offset, y_offset), special_flags=pygame.BLEND_RGB_ADD)

        # Blit the combined frame to the screen
        screen.blit(frame_surface, (0, 0))

        # Draw Earth in front if needed (drawn on screen)
        if not earth_behind:
            earth_rect = earth_display_img.get_rect()
            earth_rect.center = (int(earth_pos[0]), int(earth_pos[1]))
            screen.blit(earth_display_img, earth_rect)

        font_ingame = pygame.font.SysFont(None, 40) # Renamed to avoid conflict
        year_text = font_ingame.render(f"{displayed_year}", True, (255, 255, 255))
        screen.blit(year_text, (30, 30))

        # Draw instability bar
        bar_width = 400
        bar_height = 20
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT - bar_height - 20  # 20 pixels from bottom
        
        # Draw bar background (empty bar)
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        
        # Draw filled portion of bar
        fill_width = int((instability_counter / INSTABILITY_LIMIT) * bar_width)
        if fill_width > 0:
            pygame.draw.rect(screen, (255, 0, 0), (bar_x, bar_y, fill_width, bar_height))
        
        # Draw border around bar
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)

        if args.rotation is None: # This check needs to be inside GAME_PLAY state
            bt.reset_input_buffer()
            bt.reset_output_buffer()

        # if not game_over: # This check is implicitly handled by current_game_state == STATE_GAME_PLAY
        frame_index += rotation_speed


    elif game_state.current_state == STATE_GAME_OVER:
        # Initialize explosion if not already started
        if game_state.explosion is None:
            # Get current sun frame for explosion
            frame_base = int(frame_index) % len(sun_frames)
            current_frame = sun_frames[frame_base]
            game_state.start_explosion(
                SCREEN_WIDTH // 2 + x_drift, 
                SCREEN_HEIGHT // 2 + y_drift,
                current_frame
            )
        
        # Update and draw explosion
        if game_state.explosion and game_state.explosion.update():
            game_state.explosion.draw(screen)
        
        # Draw game over text
        font = pygame.font.SysFont(None, 120)
        text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))

        font3 = pygame.font.SysFont(None, 36)
        restart_text = font3.render("Press R to Restart", True, (255, 255, 0))
        screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 100))

        # Display years survived
        font_gameover = pygame.font.SysFont(None, 40)
        year_text_gameover = font_gameover.render(f"Years Survived: {displayed_year}", True, (255, 255, 255))
        screen.blit(year_text_gameover, (SCREEN_WIDTH // 2 - year_text_gameover.get_width() // 2, SCREEN_HEIGHT // 2 + 150))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
