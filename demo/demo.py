import pygame
import math
import random
import serial
import time
import sys


# --- TEST MODE ---
TEST_MODE = '--test' in sys.argv

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)

MIN_PUSH_STRENGTH = 0.4
MAX_PUSH_STRENGTH = 0.8

# Game window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Solar System Simulation")
clock = pygame.time.Clock()

# def send_command(command):
#     global arduino
#     if arduino and arduino.is_open:
#         arduino.write((command.strip() + '\n').encode('utf-8'))

def read_arduino_sensor_data(arduino):
    if arduino and arduino.in_waiting > 0:
        line = arduino.readline().decode('utf-8', errors='ignore').strip()
        if line:
            parts = line.split()
            if len(parts) == 7:
                try:
                    return [float(x) for x in parts]
                except ValueError:
                    print(f"Malformed float in line: {line}")
    return None

class SolarFlare:
    def __init__(self, angle):
        self.angle = angle
        self.warning_time = 2 * FPS  # 2 seconds warning
        self.active = True
        self.warning = True
        self.length = 100
        self.dx = math.cos(angle)
        self.dy = math.sin(angle)
        self.push_strength = random.uniform(MIN_PUSH_STRENGTH, MAX_PUSH_STRENGTH)  # Random strength for each flare
        self.countered = False
        self.earth_flare = False
        self.earth_target = None
    
    def update(self):
        if self.warning:
            self.warning_time -= 1
            if self.warning_time <= 0:
                self.warning = False
                self.active = True  # Activate flare after warning period
    
    def draw(self, sun_x, sun_y):
        if self.earth_flare:
            # Draw flare from Sun to Earth
            if self.warning:
                color = YELLOW if (self.warning_time // 10) % 2 == 0 else WHITE
            else:
                color = YELLOW
            pygame.draw.line(screen, color, (sun_x, sun_y), 
                           (self.earth_target.x, self.earth_target.y), 5)
        else:
            # Draw normal flare
            start_x = sun_x
            start_y = sun_y
            end_x = start_x + math.cos(self.angle) * self.length
            end_y = start_y + math.sin(self.angle) * self.length
            
            if self.warning:
                color = YELLOW if (self.warning_time // 10) % 2 == 0 else WHITE
            else:
                # Color intensity based on push strength
                intensity = int(255 * (self.push_strength / MAX_PUSH_STRENGTH))  # 0.8 is max strength
                color = (intensity, intensity, 0)  # Brighter yellow = stronger flare
            pygame.draw.line(screen, color, (start_x, start_y), (end_x, end_y), 3)

class Sun:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 40
        self.speed = 1.1
        self.color = (255, 255, 0)  # Start as pure yellow
        self.flares = []
        self.base_flare_cooldown = 100  # Base cooldown between flares
        self.flare_cooldown = self.base_flare_cooldown
        self.current_cooldown = self.flare_cooldown
        self.initial_x = x
        self.initial_y = y
        self.max_distance = 25
        self.max_flare_distance = 15
        self.earth = None
        # Movement tracking for flare frequency
        self.movement_window = []
        self.max_movement_window = 20
        self.current_movement = 0
        self.movement_threshold = 8  # Threshold for increasing flare frequency
        # Stability tracking for game over condition
        self.stability_window = []
        self.max_stability_window = 50  # Longer window for stability
        self.stability_threshold = 30  # Higher threshold for game over
        self.current_stability = 0
        # Grace period tracking
        self.grace_period = 0
        self.grace_duration = 25
    
    def move(self, dx, dy):
        # Only process player movement if there's input
        if dx != 0 or dy != 0:
            # Normalize diagonal movement to match single-key movement strength
            print(f"Moving sun dx: {dx}, dy: {dy}")
            # if dx != 0 and dy != 0 and key:
            #     dx *= 0.707  # 1/sqrt(2)
            #     dy *= 0.707  # This makes diagonal movement same strength as cardinal

            # Calculate new position from player input
            new_x = self.x + dx
            new_y = self.y + dy
            
            # Calculate distance from initial position
            distance_from_start = math.sqrt(
                (new_x - self.initial_x)**2 + 
                (new_y - self.initial_y)**2
            )
            
            # If we're too far from start, limit the movement
            if distance_from_start > self.max_distance:
                angle = math.atan2(new_y - self.initial_y, new_x - self.initial_x)
                new_x = self.initial_x + math.cos(angle) * self.max_distance
                new_y = self.initial_y + math.sin(angle) * self.max_distance
            
            # Apply screen boundaries
            old_x, old_y = self.x, self.y
            self.x = max(self.radius, min(WINDOW_WIDTH - self.radius, new_x))
            self.y = max(self.radius, min(WINDOW_HEIGHT - self.radius, new_y))
            
            # Track movement
            actual_movement = math.sqrt((self.x - old_x)**2 + (self.y - old_y)**2)
            
            # Check for active flares and grace period
            has_active_flares = any(not f.earth_flare and f.active for f in self.flares)
            
            # Update movement window for flare frequency
            if not has_active_flares and self.grace_period <= 0:
                # Track unnecessary movement
                self.movement_window.append(actual_movement)
            elif self.grace_period > 0:
                # During grace period, add minimal movement
                self.movement_window.append(actual_movement * 0.1)
            else:
                # Normal movement during active flares
                self.movement_window.append(actual_movement * 0.2)
                
            # Keep movement window at fixed size
            if len(self.movement_window) > self.max_movement_window:
                self.movement_window.pop(0)
            
            # Calculate current movement level
            self.current_movement = sum(self.movement_window)
            
            # Update stability window (tracks overall erratic movement)
            stability_factor = 1.0
            if has_active_flares:
                stability_factor = 0.5  # More lenient during active flares
            elif self.grace_period > 0:
                stability_factor = 0.2  # Very lenient during grace period
            
            self.stability_window.append(actual_movement * stability_factor)
            if len(self.stability_window) > self.max_stability_window:
                self.stability_window.pop(0)
            
            # Calculate current stability
            self.current_stability = sum(self.stability_window)
            
            # Adjust flare cooldown based on unnecessary movement
            if not has_active_flares and self.grace_period <= 0:
                # Reduce cooldown more as movement increases
                movement_ratio = min(1.0, self.current_movement / self.movement_threshold)
                min_cooldown = 20  # Minimum time between flares
                self.flare_cooldown = max(min_cooldown, 
                    self.base_flare_cooldown * (1 - movement_ratio * 0.75))  # Can reduce cooldown up to 75%
            else:
                # Gradually return to base cooldown
                self.flare_cooldown = min(self.base_flare_cooldown,
                    self.flare_cooldown + 1)
            
            # Check for counteracting flares only when player moves
            movement_magnitude = math.sqrt(dx**2 + dy**2)
            if movement_magnitude > 0:
                # Normalize the player's input direction
                move_normalized_x = dx / movement_magnitude
                move_normalized_y = dy / movement_magnitude
                
                # Check each flare for countering
                for flare in self.flares:
                    if flare.active and not flare.earth_flare and not flare.countered:
                        # Calculate dot product with player's movement direction
                        dot_product = (move_normalized_x * flare.dx + move_normalized_y * flare.dy)
                        
                        # Calculate required counter magnitude based on flare strength
                        required_magnitude = flare.push_strength * self.speed
                        
                        # Single key movement should be enough to counter
                        movement_magnitude = self.speed
                        
                        # If player is moving in opposite direction with sufficient force
                        if dot_product < -0.5 and movement_magnitude >= required_magnitude:
                            flare.countered = True
                            self.grace_period = self.grace_duration  # Start grace period when flare is countered
    
    def update(self):
        # Update grace period
        if self.grace_period > 0:
            self.grace_period -= 1

        # Check for excessive instability
        if self.current_stability > self.stability_threshold and not TEST_MODE:
            # print(f"Sun too unstable! Stability: {self.current_stability}")
            # Create instability flare targeting Earth
            earth_flare = SolarFlare(0)
            earth_flare.earth_flare = True
            earth_flare.earth_target = self.earth
            earth_flare.warning = False
            earth_flare.warning_time = 0
            earth_flare.active = True
            self.flares.append(earth_flare)
            if not TEST_MODE:
                self.earth.alive = False
                return True

        # Update flare cooldown
        self.current_cooldown -= 1
        if self.current_cooldown <= 0:
            if not any(not f.earth_flare for f in self.flares):
                angle = random.uniform(0, 2 * math.pi)
                new_flare = SolarFlare(angle)
                self.flares.append(new_flare)
                # send_command("flare")
            self.current_cooldown = self.flare_cooldown
        
        # Apply flare effects separately from player movement
        for flare in self.flares[:]:
            flare.update()
            
            if flare.active:
                if flare.earth_flare:
                    # Immediately end game when Earth is targeted
                    if not TEST_MODE:
                        self.earth.alive = False
                        return True
                else:
                    # Move the sun due to flare push
                    push_x = flare.dx * flare.push_strength
                    push_y = flare.dy * flare.push_strength
                    
                    # Calculate new position including flare push
                    new_x = self.x + push_x
                    new_y = self.y + push_y
                    
                    # Calculate distance from initial position after push
                    distance_from_start = math.sqrt(
                        (new_x - self.initial_x)**2 + 
                        (new_y - self.initial_y)**2
                    )
                    
                    # If push would move sun too far, limit the movement
                    if distance_from_start > self.max_flare_distance:
                        angle = math.atan2(new_y - self.initial_y, new_x - self.initial_x)
                        new_x = self.initial_x + math.cos(angle) * self.max_flare_distance
                        new_y = self.initial_y + math.sin(angle) * self.max_flare_distance
                    
                    # Apply screen boundaries
                    self.x = max(self.radius, min(WINDOW_WIDTH - self.radius, new_x))
                    self.y = max(self.radius, min(WINDOW_HEIGHT - self.radius, new_y))
                    
                    # Check if flare should target Earth
                    if not flare.warning and not flare.countered and not TEST_MODE:
                        earth_flare = SolarFlare(0)
                        earth_flare.earth_flare = True
                        earth_flare.earth_target = self.earth
                        earth_flare.warning = False
                        earth_flare.warning_time = 0
                        earth_flare.active = True
                        self.flares.append(earth_flare)
                        if not TEST_MODE:
                            self.earth.alive = False
                            return True
                    
                    # Remove flare if countered
                    if flare.countered:
                        self.flares.remove(flare)
        
        # Gentle return to center when no flares are active
        if not self.flares:
            dx = (self.initial_x - self.x) * 0.01
            dy = (self.initial_y - self.y) * 0.01
            self.x += dx
            self.y += dy
        
        return False
    
    def draw(self):
        # Draw the sun with color based on both flare frequency and stability
        cooldown_ratio = self.flare_cooldown / self.base_flare_cooldown
        stability_ratio = min(1.0, self.current_stability / self.stability_threshold)
        
        # More red as either flares become more frequent or stability decreases
        yellow = min(255, int(255 * cooldown_ratio * (1 - stability_ratio)))
        self.color = (255, yellow, 0)
        
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # Draw flares
        for flare in self.flares:
            flare.draw(self.x, self.y)

class Earth:
    def __init__(self, sun):
        self.sun = sun
        self.angle = 0
        self.orbit_radius = 150
        self.radius = 20
        self.orbit_speed = 0.02
        self.alive = True
    
    def update(self):
        if self.alive:
            self.angle += self.orbit_speed
            self.x = self.sun.x + math.cos(self.angle) * self.orbit_radius
            self.y = self.sun.y + math.sin(self.angle) * self.orbit_radius
    
    def draw(self):
        if self.alive:
            pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), self.radius)

def main():
    sun = Sun(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
    earth = Earth(sun)
    sun.earth = earth  # Give Sun a reference to Earth
    running = True
    game_over = False

    use_arduino_control = True  # Control flag for Arduino vs keyboard

    try:
        arduino = serial.Serial(port='COM3', baudrate=115200, timeout=1)
        time.sleep(0.5)
        arduino.reset_input_buffer()
        print('Starting Arduino serial connection...')
    except Exception as e:
        print(f"Failed to connect to Arduino: {e}")
        arduino = None

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and game_over:
                    sun = Sun(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
                    earth = Earth(sun)
                    sun.earth = earth
                    game_over = False
                elif event.key == pygame.K_TAB:
                    use_arduino_control = not use_arduino_control
                    print(f"Arduino control: {use_arduino_control}")

        if not game_over:
            if use_arduino_control:
                sensor_data = read_arduino_sensor_data(arduino)
                if sensor_data:
                    ax, ay, *_ = sensor_data
                    print(f"Sensor movement ax: {ax}, ay: {ay}")
                    scale = 0.001  # Adjust as needed for sensitivity
                    dx = ax * scale
                    dy = ay * scale
                    sun.move(dx, dy)
                else:
                    # If no Arduino data, don't move the sun
                    pass
            else:
                keys = pygame.key.get_pressed()
                dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * sun.speed
                dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * sun.speed
                sun.move(dx, dy)

            # Update sun and earth
            game_over = sun.update()
            earth.update()

        # Drawing
        screen.fill(BLACK)
        sun.draw()
        earth.draw()

        # Draw game over message
        if game_over:
            font = pygame.font.Font(None, 74)
            text = font.render('Game Over', True, RED)
            text_rect = text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/4))
            screen.blit(text, text_rect)
            
            font = pygame.font.Font(None, 36)
            text = font.render('Press R to restart', True, RED)
            text_rect = text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/4 + 50))
            screen.blit(text, text_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
