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


class EditMenu:

    # -- Init --

    def __init__(self):
        self.width   = 300
        self.padding = 20
        self.visible = False

        self.target_object = None
        self.menu_mode     = None   # "settings" | "moving_object"

        # Fonts
        self.title_font = pygame.font.Font(None, 32)
        self.label_font = pygame.font.Font(None, 24)
        self.input_font = pygame.font.Font(None, 22)

        # Colour palette
        self.bg_color = (40,  42,  54)
        self.text_color = (248, 248, 242)
        self.input_bg = (68,  71,  90)
        self.input_active = (98,  114, 164)
        self.border_color = (98,  114, 164)

        # Input fields
        self.fields = []
        self.active_field = None

        self.update_position()

    # -- Layout --

    def update_position(self):
        self.x = cfg.SCREEN_WIDTH - self.width
        self.y = 0
        self.height = cfg.SCREEN_HEIGHT

    def get_field_rect(self, field):
        return pygame.Rect(
            self.x + self.padding,
            field['y'] + 25,
            self.width - self.padding * 2,
            35,
        )

    # -- Visibility --

    def show(self, target_object=None):
        from objects import MovingObject

        self.target_object = target_object
        self.visible = True
        self.fields = []
        self.active_field = None
        self.update_position()

        if target_object is None:
            self.menu_mode = "settings"
            self._setup_settings_fields()
        elif isinstance(target_object, MovingObject):
            self.menu_mode = "moving_object"
            self._setup_moving_object_fields()

    def hide(self):
        self.visible = False
        self.target_object = None
        self.active_field  = None

    # -- Field builders --

    def _setup_settings_fields(self):
        y = 100
        spacing = 80

        # get current collision mode
        collision_mode_value = cfg.COLLISION_MODE

        for name, label, value in [
            ('collision_mode', 'Collision Mode', collision_mode_value),
            ('time_scale', 'Time Scale', cfg.TIME_SCALE),
            ('collision_elasticity', 'Collision Elasticity', cfg.COLLISION_ELASTICITY),
            ('edge_elasticity', 'Edge Elasticity', cfg.EDGE_ELASTICITY),
        ]:
            self.fields.append({
                'name': name, 'label': label,
                'value': str(value) if not isinstance(value, str) else value,
                'y': y, 'editable': True,
            })
            y += spacing

    def _setup_moving_object_fields(self):
        obj = self.target_object
        y = 100
        spacing = 80

        radius_m = obj.get_width() / (2 * cfg.PIXELS_PER_METER)

        for name, label, value in [
            ('mass', 'Mass (kg)', obj.get_mass()),
            ('radius', 'Radius (m)', radius_m),
            ('velocity_x', 'Velocity X (m/s)', obj.get_velocity_x()),
            ('velocity_y', 'Velocity Y (m/s)', obj.get_velocity_y()),
        ]:
            self.fields.append({
                'name': name, 'label': label,
                'value': str(round(value, 3)),
                'y': y, 'editable': True,
            })
            y += spacing

    # -- Event handling --

    def handle_event(self, event):
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            menu_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if not menu_rect.collidepoint(event.pos):
                return False   # click passed through to scene

            self.active_field = None
            for field in self.fields:
                if field['editable'] and self.get_field_rect(field).collidepoint(event.pos):
                    self.active_field = field
                    return True

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return "hide"

            if self.active_field:
                if event.key == pygame.K_RETURN:
                    self.apply_changes()
                    self.active_field = None
                    return "apply_changes"
                elif event.key == pygame.K_BACKSPACE:
                    self.active_field['value'] = self.active_field['value'][:-1]
                elif self.active_field['name'] == 'collision_mode':
                    # Allow 1, 2, D for collision mode (e.g., "1D", "2D")
                    if event.unicode in '12Dd':
                        self.active_field['value'] += event.unicode.upper()
                else:
                    # Normal numeric input for other fields
                    if event.unicode in '0123456789.-':
                        self.active_field['value'] += event.unicode
                return True

        return False

    # -- Apply --

    def apply_changes(self):
        try:
            if self.menu_mode == "settings":
                for field in self.fields:
                    
                    if field['name'] == 'collision_mode':
                        value = field['value'].strip().upper()
                        if value in ['1D', '2D']:
                            cfg.COLLISION_MODE = value
                            print(f"Collision mode -> {value}")
                        continue
                    
                    value = float(field['value'])

                    if field['name'] == 'time_scale' and value > 0:
                        cfg.TIME_SCALE = value
                        print(f"Time scale -> {value}")
                    
                    elif field['name'] == 'collision_elasticity' and 0 <= value <= 1:
                        cfg.COLLISION_ELASTICITY = value
                        print(f"Collision elasticity -> {value}")
                    
                    elif field['name'] == 'edge_elasticity' and 0 <= value <= 1:
                        cfg.EDGE_ELASTICITY = value
                        print(f"Edge elasticity -> {value}")

            elif self.menu_mode == "moving_object":
                obj = self.target_object
                for field in self.fields:
                    value = float(field['value'])

                    if field['name'] == 'mass' and value > 0:
                        obj.mass   = value
                        obj.gforce = [0.0, value * cfg.GRAVITY]

                    elif field['name'] == 'radius' and value > 0:
                        diameter_px = value * 2 * cfg.PIXELS_PER_METER
                        obj.radius = value
                        obj.width = diameter_px
                        obj.height = diameter_px
                        obj.rect = obj.image.get_rect(center=obj.get_center())
                        obj.set_click_hitbox()

                    elif field['name'] == 'velocity_x':
                        obj.set_velocity_x(value)

                    elif field['name'] == 'velocity_y':
                        obj.set_velocity_y(value)

            print(f"Changes applied to {self.menu_mode}")

        except ValueError as exc:
            print(f"Error applying changes: {exc}")

    # -- Drawing --

    def draw(self, screen):
        if not self.visible:
            return

        # Panel background
        pygame.draw.rect(screen, self.bg_color,
                         (self.x, self.y, self.width, self.height))
        pygame.draw.line(screen, self.border_color,
                         (self.x, self.y), (self.x, self.height), 3)

        # Title
        titles = {"settings": "Settings", "moving_object": "Edit Moving Object"}
        title_surf = self.title_font.render(
            titles.get(self.menu_mode, "Menu"), True, self.text_color
        )
        screen.blit(title_surf,
                    (self.x + (self.width - title_surf.get_width()) // 2, 30))

        # Input fields
        for field in self.fields:
            label_surf = self.label_font.render(field['label'], True, self.text_color)
            screen.blit(label_surf, (self.x + self.padding, field['y']))

            if not field['editable']:
                continue

            field_rect = self.get_field_rect(field)
            bg = self.input_active if field is self.active_field else self.input_bg
            pygame.draw.rect(screen, bg,               field_rect, border_radius=4)
            pygame.draw.rect(screen, self.border_color, field_rect, 2, border_radius=4)

            text_surf = self.input_font.render(field['value'], True, self.text_color)
            text_x = field_rect.x + 10
            text_y = field_rect.y + (field_rect.height - text_surf.get_height()) // 2
            screen.blit(text_surf, (text_x, text_y))

            if field is self.active_field:
                cursor_x = text_x + text_surf.get_width() + 2
                pygame.draw.line(screen, self.text_color,
                                 (cursor_x, field_rect.y + 5),
                                 (cursor_x, field_rect.y + field_rect.height - 5), 2)

        # Bottom instructions
        instructions = [
            "Press ENTER to save changes",
            "Press ESC to close menu",
            "",
            "Collision Mode: Type 1D or 2D",
            "",
            "Controls:",
            "RMB Click object - Edit properties",
            "RMB Click empty space - Settings",
            "F - Pause/Resume",
            "R - Reset simulation",
            "A - Add object at cursor",
            "S - Delete object at cursor",
        ]
        inst_y = self.height - 300
        for i, line in enumerate(instructions):
            surf = self.input_font.render(line, True, self.text_color)
            screen.blit(surf,
                        (self.x + (self.width - surf.get_width()) // 2,
                         inst_y + i * 25))