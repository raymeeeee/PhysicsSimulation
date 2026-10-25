# -- Libraries --
import pygame
import pygame.gfxdraw
import sys
import math
import time
import pathlib

# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

# Use config_manager
from config_manager import get_config_manager
cfg = get_config_manager()

import objects
import mymouse
import friction
import ui

pygame.init()

# -- Helpers --

def get_closest_point_on_line(point, line, offset):
    A = list(line[0])
    B = list(line[1])
    v = [A[0] - B[0], A[1] - B[1]]
    u = [point[0] - A[0], point[1] - A[1]]

    dot_uv = v[0] * u[0] + v[1] * u[1]
    v_squared = v[0] ** 2 + v[1] ** 2
    t = dot_uv / v_squared

    return [
        (A[0] + t * v[0]) + math.sin(math.radians(cfg.ANGLE)) * offset,
        (A[1] + t * v[1]) - math.cos(math.radians(cfg.ANGLE)) * offset,
    ]


def set_object_on_plane(plane, moving_object, mouse=None):
    point = mouse.get_mouse_pos() if mouse is not None else moving_object.get_center()
    top_edge = plane.get_edges()[0]
    point_on_line = get_closest_point_on_line(point, top_edge,
                                               offset=moving_object.get_height() / 2)
    moving_object.set_center(point_on_line)


def check_border_collision(x, y, plane):
    line = plane.get_edges()[0]
    A, B = line
    v = [B[0] - A[0], B[1] - A[1]]
    u = [x - A[0],    y - A[1]]
    v_squared = v[0] ** 2 + v[1] ** 2

    if v_squared == 0:
        return "none"

    t = (v[0] * u[0] + v[1] * u[1]) / v_squared

    if t < 0:
        return "left"
    if t > 1:
        return "right"
    return "none"


def set_object_before_plane(border, plane, moving_object):
    if border == "none":
        return

    corners = plane.get_rotated_corners()
    line = (corners[0], corners[1])

    # Flip: "left" overflow → place at right end (corners[0]) and vice-versa
    ref_point = corners[1] if border == "left" else corners[0]
    point_on_line = get_closest_point_on_line(ref_point, line,
                                              offset=moving_object.get_height() / 2)
    moving_object.set_center(point_on_line)


# -- Close Button --
class CloseButton:
    
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.hovered = False
        self.font = pygame.font.Font(None, 24)
        
        self.bg_color = [98, 114, 164]
        self.hover_color = [139, 157, 195]
        self.text_color = [248, 248, 242]
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                return True
        return False
    
    def draw(self, screen):
        color = self.hover_color if self.hovered else self.bg_color
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, self.text_color, self.rect, 2, border_radius=6)
        
        text_surf = self.font.render("Close (Return to Menu)", True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


# -- Main --

def main():

    # -- Window --
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Friction Simulation")
    clock = pygame.time.Clock()

    # -- Elasticity settings --
    cfg.FRICTION_COEFFICIENT = 0.3 # Friction between object and a plane
    cfg.ANGLE = 0.0 # Angle of a plane

    # -- Scene objects --
    plane = objects.StaticObject(
        height=0.5,
        width=cfg.SCREEN_HEIGHT / cfg.PIXELS_PER_METER,
        color=cfg.COLORS["BLACK"],
        pos_x=cfg.SCREEN_WIDTH  / 2,
        pos_y=cfg.SCREEN_HEIGHT / 2,
    )
    plane.rotate_by(cfg.ANGLE)

    diameter       = 0.5   # metres
    moving_object  = objects.MovingObject(
        color=cfg.COLORS["WHITE"],
        pos_x=cfg.SCREEN_WIDTH  / 2,
        pos_y=cfg.SCREEN_HEIGHT / 2 - diameter * cfg.PIXELS_PER_METER,
        mass=10,
        radius=diameter/2,
    )

    static_objects = pygame.sprite.Group()
    moving_objects = pygame.sprite.Group()
    static_objects.add(plane)
    moving_objects.add(moving_object)

    edit_list  = [moving_object, plane]
    edges_list = [plane]

    # -- Subsystems --
    friction_manager = friction.FrictionManager(
        plane=plane,
        plane_angle=cfg.ANGLE,
        moving_object=moving_object,
        friction_coefficient=cfg.FRICTION_COEFFICIENT,
    )

    mouse     = mymouse.Mouse()
    edit_menu = ui.EditMenu()
    
    # Close button
    close_button = CloseButton(10, 10, 220, 40)

    # -- Simulation state --
    simulation_started = False
    simulation_paused = True

    physics_timestep = 1.0 / cfg.PHYSICS_FPS
    accumulator = 0.0
    last_time = time.perf_counter()

    fps_counter = 0
    fps_timer = time.time()
    current_fps = 0

    # -- Local helpers --

    def reset_simulation():
        nonlocal simulation_started, simulation_paused
        simulation_started = False
        simulation_paused  = True
        moving_object.set_velocity_x(0)
        moving_object.set_velocity_y(0)
        moving_object.distance_travelled = 0
        print("Simulation reset")

    # -- Main loop --

    run = True
    while run:

        # -- Timing --
        current_time = time.perf_counter()
        dt = current_time - last_time
        last_time = current_time

        if simulation_started and not simulation_paused:
            accumulator += dt * cfg.TIME_SCALE
        else:
            accumulator = 0.0

        # -- Events --
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            
            # Close button takes priority
            if close_button.handle_event(event):
                print("Returning to main menu...")
                run = False
                continue

            # Edit menu takes priority
            menu_result = edit_menu.handle_event(event)

            if menu_result == "apply_changes":
                # Reset simulation when settings change (includes plane parameters)
                if edit_menu.menu_mode == "settings":
                    print("Updating plane from settings...")
                    plane.rotation_angle = 0
                    plane.rotate_by(cfg.ANGLE)

                    friction_manager.plane_angle = cfg.ANGLE
                    friction_manager.angle_rad   = math.radians(cfg.ANGLE)
                    friction_manager.friction_coefficient = cfg.FRICTION_COEFFICIENT

                    set_object_on_plane(plane, moving_object)
                    reset_simulation()
                    print("Plane updated, simulation reset")
                
                accumulator = 0.0
                continue

            if menu_result:
                continue

            # -- Right-click → open edit menu --
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                mouse_pos     = pygame.mouse.get_pos()

                # if moving object is clicked -> open menu for moving object
                if moving_object.click_hitbox.collidepoint(mouse_pos):
                    edit_menu.show(moving_object)
                # if empty space is clicked -> open general menu for simulation
                else:
                    edit_menu.show()

            # -- Keyboard --
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    edit_menu.hide()

                if event.key == pygame.K_f:
                    simulation_paused  = not simulation_paused
                    simulation_started = not simulation_started

                if event.key == pygame.K_r:
                    reset_simulation()

        # -- Drag-and-drop --
        if mouse.is_lmb_clicked() and simulation_paused:
            mouse_pos = mouse.get_mouse_pos()

            if mouse.draggable_object is None:
                # Try to pick up an object under the cursor
                if moving_object.click_hitbox.collidepoint(mouse_pos):
                    mouse.draggable_object = moving_object
            else:
                # Move the held object to the cursor, then snap it onto the plane
                mouse.draggable_object.set_center(mouse_pos)
                border = check_border_collision(*mouse_pos, plane)
                if border != "none":
                    set_object_before_plane(border, plane, mouse.draggable_object)
                else:
                    set_object_on_plane(plane, mouse.draggable_object)

        elif not mouse.is_lmb_clicked() and simulation_paused:
            # Drop: sync logical position if an object was being dragged
            if mouse.draggable_object is not None:
                mouse.draggable_object.sync_logical_to_visual()
                mouse.draggable_object.set_velocity_x(0)
                mouse.draggable_object.set_velocity_y(0)
            mouse.draggable_object = None


        # -- Physics --
        physics_steps = 0
        while accumulator >= physics_timestep and physics_steps < 1:
            if simulation_started and not simulation_paused:
                x, y   = moving_object.get_center()
                border = check_border_collision(x, y, plane)
                if border != "none":
                    set_object_before_plane(border, plane, moving_object)

                # Clamp near-zero motion to a full stop
                if (abs(moving_object.get_acceleration_x()) < 0.1
                        and abs(moving_object.get_acceleration_y()) < 0.1
                        and abs(moving_object.get_velocity_x())     < 0.1
                        and abs(moving_object.get_velocity_y())     < 0.1):
                    moving_object.set_velocity_x(0)
                    moving_object.set_velocity_y(0)

                force_x, force_y = friction_manager.calculate_forces()
                moving_object.resolve_forces((force_x, force_y))
                moving_object.update_physics(physics_timestep)

            accumulator   -= physics_timestep
            physics_steps += 1


        # -- Rendering --
        screen.fill(cfg.COLORS["WHITE"])

        plane.draw(screen)
        moving_object.draw(screen)

        # Plane edges
        for static_obj in edges_list:
            for edge in static_obj.edges:
                pygame.draw.line(screen, (255, 0, 255), edge[0], edge[1], 2)

        # Draw click hitboxes (debug)
        pygame.draw.rect(screen, cfg.COLORS["GREEN"], moving_object.click_hitbox, 1)

        # Velocity arrow
        center = moving_object.get_center()
        pygame.draw.circle(screen, (0, 0, 255), (int(center[0]), int(center[1])), 5)

        vel_x, vel_y = moving_object.get_velocity_x(), moving_object.get_velocity_y()
        pygame.draw.line(
            screen, (0, 0, 255),
            center,
            (center[0] + vel_x * 10, center[1] + vel_y * 10),
            2,
        )

        # Edit menu overlay
        edit_menu.draw(screen)
        
        # Close button
        close_button.draw(screen)

        # -- HUD --
        font      = pygame.font.Font(None, 24)
        sim_state = ("RUNNING" if simulation_started and not simulation_paused
                     else "PAUSED")
        hud_lines = [
            f"Graphics FPS: {current_fps}/{cfg.FPS}",
            f"Physics FPS: {cfg.PHYSICS_FPS}",
            f"Distance travelled: {moving_object.distance_travelled:.3f} m",
            f"Velocity X: {moving_object.get_velocity_x():.2f} m/s",
            f"Velocity Y: {moving_object.get_velocity_y():.2f} m/s",
            f"Acceleration X: {moving_object.acceleration_x:.2f} m/s²",
            f"Acceleration Y: {moving_object.acceleration_y:.2f} m/s²",
            f"Mass: {moving_object.mass} kg",
            f"Plane angle: {cfg.ANGLE}°",
            f"Friction coefficient: {cfg.FRICTION_COEFFICIENT}",
            f"Time Scale: {cfg.TIME_SCALE}x",
            f"Simulation: {sim_state}",
        ]
        for i, line in enumerate(hud_lines):
            surf = font.render(line, True, cfg.COLORS["GREEN"])
            screen.blit(surf, (10, 300 + i * 25))
            

        # -- FPS counter --
        fps_counter += 1
        if time.time() - fps_timer >= 1.0:
            current_fps = fps_counter
            fps_counter = 0
            fps_timer   = time.time()

        pygame.display.flip()
        clock.tick(cfg.FPS)

    pygame.quit()

if __name__ == "__main__":
    main()