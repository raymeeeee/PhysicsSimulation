import math
import pygame
import pathlib
import sys
# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

# Use config_manager
from config_manager import get_config_manager
cfg = get_config_manager()
import objects


class String:

    def __init__(self, start_x, start_y, elasticity_modulus, natural_length, particle):
        self.start_x = start_x
        self.start_y = start_y
        self.elasticity_modulus  = elasticity_modulus
        self.natural_length = natural_length
        self.particle = particle

        self.elasticity_coefficient = elasticity_modulus / natural_length

        # logical anchor position in meters
        self.logical_start_x = start_x / cfg.PIXELS_PER_METER
        self.logical_start_y = start_y / cfg.PIXELS_PER_METER

        # camera offset for panning / zooming
        self.camera_offset_x = 0.0
        self.camera_offset_y = 0.0

        # small visible radius for the anchor dot and its click hitbox (10cm)
        self.radius = 0.1  # metres
        self.click_hitbox = self._make_hitbox()

    # -- Hitbox --

    def _make_hitbox(self):
        side = self.radius * cfg.PIXELS_PER_METER * math.sqrt(2)
        return pygame.Rect(
            self.start_x - side / 2,
            self.start_y - side / 2,
            side, side,
        )

    def set_click_hitbox(self):
        self.click_hitbox = self._make_hitbox()

    # -- Position --

    def get_center(self): return (self.start_x, self.start_y)

    def set_center(self, position):
        self.start_x, self.start_y = position[0], position[1]
        # Account for camera offset when calculating logical position
        self.logical_start_x = (self.start_x - self.camera_offset_x) / cfg.PIXELS_PER_METER
        self.logical_start_y = (self.start_y - self.camera_offset_y) / cfg.PIXELS_PER_METER
        self.click_hitbox = self._make_hitbox()

    def sync_logical_to_visual(self):
        self.logical_start_x = (self.start_x - self.camera_offset_x) / cfg.PIXELS_PER_METER
        self.logical_start_y = (self.start_y - self.camera_offset_y) / cfg.PIXELS_PER_METER

    def apply_camera_offset(self, delta_x, delta_y):
        self.camera_offset_x += delta_x
        self.camera_offset_y += delta_y
        # Update visual position from logical + camera offset
        self.start_x = self.logical_start_x * cfg.PIXELS_PER_METER + self.camera_offset_x
        self.start_y = self.logical_start_y * cfg.PIXELS_PER_METER + self.camera_offset_y
        # Update hitbox directly
        self.click_hitbox = self._make_hitbox()

    def update_visual_position(self):
        self.start_x = self.logical_start_x * cfg.PIXELS_PER_METER + self.camera_offset_x
        self.start_y = self.logical_start_y * cfg.PIXELS_PER_METER + self.camera_offset_y
        self.set_center((self.start_x, self.start_y))

    # -- Physics --

    def calculate_extension(self):
        px, py   = self.particle.get_logical_position()
        distance = math.hypot(self.logical_start_x - px, self.logical_start_y - py)
        return distance - self.natural_length

    def calculate_angle(self):
        px, py = self.particle.get_logical_position()
        return math.atan2(self.logical_start_y - py, self.logical_start_x - px)

    def calculate_tension(self):
        extension = self.calculate_extension()
        if extension <= 0:
            return (0.0, 0.0)

        tension = self.elasticity_coefficient * extension
        angle   = self.calculate_angle()
        return (math.cos(angle) * tension, math.sin(angle) * tension)
    
    def calcualte_elastic_potential_energy(self):
        # EPE = ʎx^2 / 2l where ʎ is modulus of elasticity, l is natural length, x is extension
        return (self.elasticity_modulus*(self.calculate_extension()**2))/(2*self.natural_length)

    # -- Drawing --

    def draw(self, surface):
        color = cfg.COLORS["RED"] if self.calculate_extension() > 0 else cfg.COLORS["BLUE"]
        pygame.draw.circle(surface, cfg.COLORS["GREEN"],
                           (int(self.start_x), int(self.start_y)),
                           int(self.radius * cfg.PIXELS_PER_METER))
        pygame.draw.aaline(surface, color,
                           (self.start_x, self.start_y),
                           self.particle.get_center())
