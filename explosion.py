import pygame
import math
import random

class Particle:
    def __init__(self, x, y, angle, speed, color, size):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.color = color
        self.size = size
        self.life = 1.0  # Life from 1 to 0
        self.decay_rate = 0.02  # How fast particle fades
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= self.decay_rate
        self.size = max(0, self.size - 0.5)
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * self.life)
        color_with_alpha = (*self.color, alpha)
        particle_surface = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, color_with_alpha, 
                         (int(self.size), int(self.size)), 
                         int(self.size))
        surface.blit(particle_surface, 
                    (int(self.x - self.size), int(self.y - self.size)))

class ImageParticle(Particle):
    def __init__(self, x, y, angle, speed, image_piece, size):
        super().__init__(x, y, angle, speed, (255, 255, 255), size)  # Color unused for image particles
        self.image = image_piece
        self.rotation = 0
        self.rotation_speed = random.uniform(-5, 5)  # Degrees per frame
        
    def draw(self, surface):
        if self.life <= 0:
            return
            
        # Create circular mask
        mask_size = int(self.size * 2)
        mask = pygame.Surface((mask_size, mask_size), pygame.SRCALPHA)
        
        # Scale image to fit the mask
        scaled_image = pygame.transform.scale(self.image, (mask_size, mask_size))
        
        # Create circular mask
        pygame.draw.circle(mask, (255, 255, 255, int(255 * self.life)), 
                         (mask_size//2, mask_size//2), mask_size//2)
        
        # Apply mask to image
        scaled_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        # Rotate
        self.rotation += self.rotation_speed
        rotated = pygame.transform.rotate(scaled_image, self.rotation)
        
        # Calculate position accounting for rotation
        pos_x = int(self.x - rotated.get_width() / 2)
        pos_y = int(self.y - rotated.get_height() / 2)
        surface.blit(rotated, (pos_x, pos_y))

class ExplosionSystem:
    def __init__(self, x, y, sun_frame=None):
        self.particles = []
        self.x = x
        self.y = y
        self.is_active = True
        self.sun_frame = sun_frame
        self.create_explosion()

    def split_image_into_pieces(self, image, num_pieces_x, num_pieces_y):
        pieces = []
        piece_width = image.get_width() // num_pieces_x
        piece_height = image.get_height() // num_pieces_y
        
        for y in range(num_pieces_y):
            for x in range(num_pieces_x):
                # Create surface for this piece
                piece = pygame.Surface((piece_width, piece_height), pygame.SRCALPHA)
                # Copy the corresponding part of the image
                piece.blit(image, (0, 0), 
                          (x * piece_width, y * piece_height, piece_width, piece_height))
                pieces.append(piece)
        
        return pieces

    def create_explosion(self):
        # Create image-based particles if we have a sun frame
        if self.sun_frame:
            # Split the sun frame into pieces
            pieces = self.split_image_into_pieces(self.sun_frame, 8, 8)  # 64 pieces
            piece_size = self.sun_frame.get_width() // 16  # Make pieces smaller for better circle effect
            
            for i, piece in enumerate(pieces):
                # Calculate position relative to center
                grid_x = (i % 8) - 4  # -4 to 3
                grid_y = (i // 8) - 4  # -4 to 3
                
                # Calculate angle based on position
                angle = math.atan2(grid_y, grid_x)
                # Add some randomness to the angle
                angle += random.uniform(-0.2, 0.2)
                
                # Speed based on distance from center
                distance = math.sqrt(grid_x**2 + grid_y**2)
                speed = random.uniform(5, 15) * (distance / 5.6)  # 5.6 is max distance from center
                
                # Create particle with image piece
                self.particles.append(ImageParticle(
                    self.x + grid_x * 20,  # Spread out initial positions
                    self.y + grid_y * 20,
                    angle,
                    speed,
                    piece,
                    piece_size
                ))
        
        # Add some regular particles for additional effect
        num_particles = 50
        for i in range(num_particles):
            angle = (i / num_particles) * (2 * math.pi)
            speed = random.uniform(5, 15)
            color = (255, random.randint(100, 200), 0)  # Orange-yellow variations
            size = random.uniform(10, 30)
            self.particles.append(Particle(self.x, self.y, angle, speed, color, size))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        return bool(self.particles)  # Return true as long as there are active particles

    def draw(self, surface):
        for particle in self.particles:
            particle.draw(surface) 