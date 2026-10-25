import pygame
import sys
import pathlib
# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

# use config_manager
from config_manager import get_config_manager
cfg = get_config_manager()
import math


class Entity(pygame.sprite.Sprite):
    def __init__(self, height, width):
        pygame.sprite.Sprite.__init__(self)
        self.height = height * cfg.PIXELS_PER_METER
        self.width  = width  * cfg.PIXELS_PER_METER

    def get_height(self): return self.height
    def get_width(self):  return self.width


class StaticObject(Entity):
    def __init__(self, height, width, color, pos_x, pos_y):
        super().__init__(height, width)

        self.pos_x = pos_x
        self.pos_y = pos_y
        self.color = color
        self.rotation_angle = 0

        # pygame sprite requires image + rect even when drawing manually
        self.image = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect  = self.image.get_rect(center=(pos_x, pos_y))

        self.rotated_corners = None
        self.edges = self._compute_edges()

    # -- Geometry --

    def _compute_edges(self):
        hw = self.width  / 2
        hh = self.height / 2

        corners_local = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]

        a = math.radians(self.rotation_angle)
        cos = math.cos(a)
        sin = math.sin(a)

        self.rotated_corners = [
            (self.pos_x + x * cos - y * sin,
             self.pos_y + x * sin + y * cos)
            for x, y in corners_local
        ]

        return [(self.rotated_corners[i], self.rotated_corners[(i + 1) % 4])
                for i in range(4)]

    def get_edges(self):           return self.edges
    def get_rotated_corners(self): return self.rotated_corners

    def rotate_by(self, angle):
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.edges = self._compute_edges()
        self.rect.center = (self.pos_x, self.pos_y)

    # -- Position --

    def get_center(self): return (self.pos_x, self.pos_y)

    def set_center(self, position):
        self.pos_x, self.pos_y = position
        self.rect.center = position
        self.edges = self._compute_edges()  # rebuilds rotated_corners

    # -- Drawing --

    def draw(self, screen):
        if self.rotated_corners:
            pygame.draw.polygon(screen, self.color,
                                [(int(x), int(y)) for x, y in self.rotated_corners])


class MovingObject(Entity):

    def __init__(self, radius, color, pos_x, pos_y, mass):
        diameter = radius * 2
        super().__init__(diameter, diameter)

        self.mass   = mass
        self.radius = radius
        self.color  = color

        self.velocity_x     = 0.0
        self.velocity_y     = 0.0
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0

        self.gforce = [0.0, mass * cfg.GRAVITY]

        self.logical_x = pos_x / cfg.PIXELS_PER_METER
        self.logical_y = pos_y / cfg.PIXELS_PER_METER
        self.pos_x     = float(pos_x)
        self.pos_y     = float(pos_y)

        self.distance_travelled = 0.0

        # for pygame sprite
        self.image = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = self.image.get_rect(center=(pos_x, pos_y))
        
        self.click_hitbox = self._make_hitbox()

    # -- Hitbox --

    def _make_hitbox(self):
        r_px = self.radius * cfg.PIXELS_PER_METER
        side = r_px * math.sqrt(2) # largest square inscribed in circle
        return pygame.Rect(
            self.pos_x - side / 2,
            self.pos_y - side / 2,
            side, side,
        )

    # -- Position helpers --

    def get_center(self): return (self.pos_x, self.pos_y)

    def set_center(self, position):
        self.pos_x, self.pos_y = float(position[0]), float(position[1])
        self.rect.center       = (self.pos_x, self.pos_y)
        self.logical_x         = self.pos_x / cfg.PIXELS_PER_METER
        self.logical_y         = self.pos_y / cfg.PIXELS_PER_METER
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
        
        self.logical_x += (self.velocity_x + 0.5 * self.acceleration_x * dt) * dt # suvat equation: s=v*t+0.5*a*t^2
        self.logical_y += (self.velocity_y + 0.5 * self.acceleration_y * dt) * dt

        self.velocity_x += self.acceleration_x * dt
        self.velocity_y += self.acceleration_y * dt

        self.pos_x = self.logical_x * cfg.PIXELS_PER_METER
        self.pos_y = self.logical_y * cfg.PIXELS_PER_METER

        dx = self.logical_x - prev_x # meters
        dy = self.logical_y - prev_y # meters
        self.distance_travelled += math.sqrt(dx * dx + dy * dy) # meters

        self.set_center((self.pos_x, self.pos_y))

    def set_velocity_along_plane(self, magnitude, angle_degrees):
        angle_rad = math.radians(angle_degrees)
        self.velocity_x = magnitude * math.cos(angle_rad)
        self.velocity_y = magnitude * math.sin(angle_rad)

    # -- Getters / setters --

    def get_mass(self): return self.mass
    def get_velocity_x(self): return self.velocity_x
    def get_velocity_y(self): return self.velocity_y
    def get_acceleration_x(self): return self.acceleration_x
    def get_acceleration_y(self): return self.acceleration_y
    def set_velocity_x(self, v): self.velocity_x = v
    def set_velocity_y(self, v): self.velocity_y = v
    def get_gforce(self): return self.gforce
    def get_pos_x(self): return self.pos_x
    def get_pos_y(self): return self.pos_y
    def get_diameter(self): return self.radius * 2

    # -- Drawing --

    def draw(self, screen):
        r_px = int(self.radius * cfg.PIXELS_PER_METER)
        cx = int(self.pos_x)
        cy = int(self.pos_y)
        pygame.draw.circle(screen, cfg.COLORS["BLACK"], (cx, cy), r_px, 3)
        pygame.draw.circle(screen, cfg.COLORS["BLACK"], (cx, cy), r_px * 0.75, 3)