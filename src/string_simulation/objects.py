import pygame
import pygame.gfxdraw
import pathlib
import sys
# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

# Use config_manager
from config_manager import get_config_manager
cfg = get_config_manager()
import math


class Entity(pygame.sprite.Sprite):

    def __init__(self, height, width):
        pygame.sprite.Sprite.__init__(self)
        self.height = height * cfg.PIXELS_PER_METER
        self.width = width * cfg.PIXELS_PER_METER

    def get_height(self): return self.height
    def get_width(self):  return self.width


class MovingObject(Entity):
    def __init__(self, radius, color, pos_x, pos_y, mass):
        diameter = radius * 2
        super().__init__(diameter, diameter)

        self.mass = mass
        self.radius = radius
        self.color = color

        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0

        self.gforce = [0.0, mass * cfg.GRAVITY]

        self.logical_x = pos_x / cfg.PIXELS_PER_METER
        self.logical_y = pos_y / cfg.PIXELS_PER_METER
        self.pos_x = float(pos_x)
        self.pos_y = float(pos_y)

        self.camera_offset_x = 0.0
        self.camera_offset_y = 0.0

        self.distance_travelled = 0.0

        # Transparent sprite surface so the object can live in a Group if needed
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

    def set_click_hitbox(self):
        self.click_hitbox = self._make_hitbox()

    # -- Position --

    def set_center(self, position):
        self.pos_x, self.pos_y = float(position[0]), float(position[1])
        self.rect.center = (self.pos_x, self.pos_y)
        # Account for camera offset when calculating logical position
        self.logical_x = (self.pos_x - self.camera_offset_x) / cfg.PIXELS_PER_METER
        self.logical_y = (self.pos_y - self.camera_offset_y) / cfg.PIXELS_PER_METER
        self.click_hitbox = self._make_hitbox()

    def get_logical_position(self): return (self.logical_x, self.logical_y)

    def sync_logical_to_visual(self):
        self.logical_x = (self.pos_x - self.camera_offset_x) / cfg.PIXELS_PER_METER
        self.logical_y = (self.pos_y - self.camera_offset_y) / cfg.PIXELS_PER_METER

    def apply_camera_offset(self, delta_x, delta_y):
        self.camera_offset_x += delta_x
        self.camera_offset_y += delta_y
        # Update visual position from logical + camera offset
        self.pos_x = self.logical_x * cfg.PIXELS_PER_METER + self.camera_offset_x
        self.pos_y = self.logical_y * cfg.PIXELS_PER_METER + self.camera_offset_y
        # Update rect and hitbox directly
        self.rect.center  = (self.pos_x, self.pos_y)
        self.click_hitbox = self._make_hitbox()

    # -- Physics --

    def resolve_forces(self, *forces):
        fx, fy = 0.0, 0.0
        for f in forces:
            fx += f[0]
            fy += f[1]
        self.acceleration_x = fx / self.mass
        self.acceleration_y = fy / self.mass

    def update_physics(self, dt):
        # -- Simple physics --

        # previous position to calculate change
        prev_x, prev_y = self.logical_x, self.logical_y

        self.velocity_x += self.acceleration_x * dt
        self.velocity_y += self.acceleration_y * dt

        self.logical_x += (self.velocity_x) * dt
        self.logical_y += (self.velocity_y) * dt

        self.pos_x = self.logical_x * cfg.PIXELS_PER_METER + self.camera_offset_x # + camera offset to maintain consistency of the physics
        self.pos_y = self.logical_y * cfg.PIXELS_PER_METER + self.camera_offset_y # + camera offset to maintain consistency of the physics

        dx = self.logical_x - prev_x # meters
        dy = self.logical_y - prev_y # meters

        self.distance_travelled += math.sqrt(dx * dx + dy * dy) # meters

        self.set_center((self.pos_x, self.pos_y))

    def reset_speed(self):
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0

    # -- Getters / setters --

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

    # -- Mutation --

    def add_point(self, position):
        self.points.add((int(position[0]), int(position[1])))
        if len(self.points) > self.max_points:
            self.points.pop()

    def clear(self):
        self.points.clear()

    # -- Transforms (for camera pan / zoom) --

    def translate_points(self, delta_x, delta_y):
        self.points = {(x + delta_x, y + delta_y) for x, y in self.points}

    def scale_points(self, zoom_center, zoom_ratio):
        cx, cy = zoom_center
        self.points = {
            (cx + (x - cx) * zoom_ratio, cy + (y - cy) * zoom_ratio)
            for x, y in self.points
        }

    # -- Drawing --

    def draw(self, screen):
        w, h = screen.get_width(), screen.get_height()
        points_to_remove = set()
        for point in self.points:
            x, y = int(point[0]), int(point[1])
            if -200 < x < w + 200 and -200 < y < h + 200:
                try:
                    pygame.gfxdraw.pixel(screen, x, y, self.color)
                except (OverflowError, ValueError, TypeError):
                    points_to_remove.add(point)
        self.points -= points_to_remove

    def length(self): return len(self.points)
