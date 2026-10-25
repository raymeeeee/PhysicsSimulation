import pygame
import pygame.gfxdraw
import pathlib
import sys
import math

# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

# Use config_manager
from config_manager import get_config_manager
cfg = get_config_manager()


class Entity(pygame.sprite.Sprite):

    def __init__(self, height, width):
        pygame.sprite.Sprite.__init__(self)
        self.height = height * cfg.PIXELS_PER_METER
        self.width = width * cfg.PIXELS_PER_METER

    def get_height(self): return self.height
    def get_width(self):  return self.width


class StaticObject(Entity):
    def __init__(self, height, width, color, pos_x, pos_y, elasticity):
        super().__init__(height, width)

        self.color = color
        self.elasticity = elasticity
        self.pos_x = pos_x
        self.pos_y = pos_y

        # needed for pygames sprite groups
        self.image = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = self.image.get_rect(center=(pos_x, pos_y))

        self.edges = self._compute_edges()

    # -- Geometry --

    def _compute_edges(self):
        hw = self.width  / 2
        hh = self.height / 2

        # four corners of the axis-aligned rectangle
        corners = [
            (self.pos_x - hw, self.pos_y - hh),  # top-left
            (self.pos_x + hw, self.pos_y - hh),  # top-right
            (self.pos_x + hw, self.pos_y + hh),  # bottom-right
            (self.pos_x - hw, self.pos_y + hh)   # bottom-left
        ]

        # return edges as pairs of consecutive corners
        return [(corners[i], corners[(i + 1) % 4])
                for i in range(4)]

    def get_edges(self): return self.edges

    # -- Position --

    def get_center(self): return (self.pos_x, self.pos_y)

    def set_center(self, position):
        self.pos_x, self.pos_y = position[0], position[1]
        self.rect.center = position
        self.edges = self._compute_edges()

    # -- Misc --

    def get_elasticity(self): return self.elasticity

    def set_image(self, image):
        self.image = pygame.transform.smoothscale(image, (int(self.width), int(self.height)))
        self.edges = self._compute_edges()

    def set_color(self, color):
        self.color = color
        self.image.fill(color)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)


class MovingObject(Entity):
    def __init__(self, radius, color, pos_x, pos_y, elasticity, mass):
        diameter = radius * 2 # meters
        super().__init__(diameter, diameter) # height, width that are stored in pixels 

        self.mass   = mass
        self.radius = radius # metres

        self.pos_x = pos_x
        self.pos_y = pos_y

        self.color = color
        self.elasticity = elasticity

        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0

        self.gforce = [0.0, mass * cfg.GRAVITY]
        

        # image needed for pygame sprites
        self.image = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = self.image.get_rect(center=(pos_x, pos_y))

        # logical position in meters (used by the physics integrator)
        self.logical_x = pos_x / cfg.PIXELS_PER_METER
        self.logical_y = pos_y / cfg.PIXELS_PER_METER

        self.click_hitbox = self._make_hitbox()

        self.distance_travelled = 0.0

    # -- Hitbox --

    def _make_hitbox(self):
        side = self.radius * cfg.PIXELS_PER_METER * math.sqrt(2)
        return pygame.Rect(self.pos_x - side / 2, self.pos_y - side / 2, side, side)

    def set_click_hitbox(self):
        self.click_hitbox = self._make_hitbox()

    # -- Position --

    def set_center(self, position):
        self.pos_x, self.pos_y = position[0], position[1]
        self.rect.center       = position
        self.click_hitbox      = self._make_hitbox()

    def get_logical_position(self): return (self.logical_x, self.logical_y)

    def sync_logical_to_visual(self):
        self.logical_x = self.pos_x / cfg.PIXELS_PER_METER
        self.logical_y = self.pos_y / cfg.PIXELS_PER_METER

    # -- Physics --

    def resolve_forces(self, *forces):
        fx, fy = 0.0, 0.0
        for f in forces:
            fx += f[0]
            fy += f[1]

        self.acceleration_x = fx / self.mass
        self.acceleration_y = fy / self.mass

    def update_physics(self, dt):
        prev_x, prev_y  = self.logical_x, self.logical_y

        self.logical_x += (self.velocity_x + 0.5 * self.acceleration_x * dt) * dt # suvat equation: s=v*t+0.5*a*t^2 -> s=(v+0.5at)t
        self.logical_y += (self.velocity_y + 0.5 * self.acceleration_y * dt) * dt

        self.velocity_x += self.acceleration_x * dt
        self.velocity_y += self.acceleration_y * dt
        
        self.pos_x = self.logical_x * cfg.PIXELS_PER_METER
        self.pos_y = self.logical_y * cfg.PIXELS_PER_METER

        dx = self.logical_x - prev_x # meters
        dy = self.logical_y - prev_y # meters
        self.distance_travelled += math.sqrt(dx * dx + dy * dy) # meters

        self.set_center((self.pos_x, self.pos_y))

        

    def reset_speed(self):
        self.velocity_x     = 0.0
        self.velocity_y     = 0.0
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0

    def check_should_stop(self, ground_y, threshold_height=0.02):
        # calculate total kinetic energy (only vertical component because calculation is for rebound)
        total_ke_y = 0.5 * self.mass * (self.velocity_y ** 2) #(self.velocity_x ** 2 + self.velocity_y ** 2)
        
        # calculate gravitational potential energy
        radius_px = self.radius * cfg.PIXELS_PER_METER
        ball_bottom_y = self.pos_y + radius_px
        
        # height above ground (reference: ground surface)
        height_above_ground_px = ground_y - ball_bottom_y
        height_above_ground_m = height_above_ground_px / cfg.PIXELS_PER_METER
        
        # GPE (can be negative if ball is below ground due to penetration)
        gpe = self.mass * cfg.GRAVITY * height_above_ground_m
        
        # total mechanical energy (ke+gpe)
        total_energy = total_ke_y + gpe
        
        # convert total energy to equivalent height
        # this makes the threshold mass-independent
        if cfg.GRAVITY > 0 and self.mass > 0:
            equivalent_height = total_energy / (self.mass * cfg.GRAVITY)
        else:
            equivalent_height = float('inf')
        
        # stop if total energy is too low
        # default: equivalent to bouncing less than 2cm (0.02m)
        insufficient_energy = equivalent_height < threshold_height
        
        return insufficient_energy
    
    def calculate_ke(self):
        return 0.5 * self.mass * (self.velocity_y ** 2 + self.velocity_x** 2) # 0.5*m*(sqrt(vx^2+vy^))2 -> 0.5m(vx^2+vy^2)

    # -- Getters / Setters --

    def get_center(self): return (self.pos_x, self.pos_y)
    def get_mass(self): return self.mass
    def get_velocity_x(self): return self.velocity_x
    def get_velocity_y(self): return self.velocity_y
    def get_acceleration_x(self): return self.acceleration_x
    def get_acceleration_y(self): return self.acceleration_y
    def set_velocity_x(self, v): self.velocity_x = v
    def set_velocity_y(self, v): self.velocity_y = v
    def set_acceleration_x(self, a): self.acceleration_x = a
    def set_acceleration_y(self, a): self.acceleration_y = a
    def get_gforce(self): return self.gforce

    # -- Drawing --

    def draw(self, screen):
        r_px = int(self.radius * cfg.PIXELS_PER_METER)
        cx = int(self.pos_x)
        cy = int(self.pos_y)
        pygame.draw.circle(screen, cfg.COLORS["BLACK"], (cx, cy), r_px, 3)
        pygame.draw.circle(screen, cfg.COLORS["BLACK"], (cx, cy), r_px * 0.75, 3)


class TrailSystem:

    def __init__(self, max_points=5000):
        self.points = set()
        self.max_points = max_points
        self.color = cfg.COLORS["RED"]

    def add_point(self, position):
        self.points.add((int(position[0]), int(position[1])))
        if len(self.points) > self.max_points:
            self.points.pop()

    def clear(self):  self.points.clear()
    def length(self): return len(self.points)

    def draw(self, screen):
        w, h             = screen.get_width(), screen.get_height()
        points_to_remove = set()
        for point in self.points:
            x, y = int(point[0]), int(point[1])

            # if trail point is far away of the screen -> do not draw it
            if -200 < x < w + 200 and -200 < y < h + 200:
                try:
                    pygame.gfxdraw.pixel(screen, x, y, self.color)
                except (OverflowError, ValueError, TypeError):
                    points_to_remove.add(point)
        self.points -= points_to_remove