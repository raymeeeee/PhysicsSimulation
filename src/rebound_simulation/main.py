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
import collisions
import ui

pygame.init()


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


def main():

    # -- Window --
    screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    pygame.display.set_caption("Collision Simulation")
    clock  = pygame.time.Clock()

    # -- Collision mode --
    cfg.COLLISION_MODE = "2D"  # "1D" or "2D"
    
    # 1D track position (center of screen)
    TRACK_Y = cfg.SCREEN_HEIGHT / 2

    # -- Elasticity settings --
    cfg.COLLISION_ELASTICITY = 1.0  # circle-circle collision elasticity
    cfg.EDGE_ELASTICITY = 1.0       # wall collision elasticity

    # -- Border walls --
    edge_size = 1.0   # metres
    
    # calculate actual ground surface position
    # edge_bottom center is at cfg.SCREEN_HEIGHT
    # edge_bottom height is edge_size meters
    # top surface of ground is at center - (height/2)
    GROUND_SURFACE_Y = cfg.SCREEN_HEIGHT - (edge_size/2 * cfg.PIXELS_PER_METER )

    edge_left   = objects.StaticObject(cfg.SCREEN_HEIGHT / cfg.PIXELS_PER_METER, edge_size,
                                       cfg.COLORS["BLACK"], 0,                    cfg.SCREEN_HEIGHT / 2,
                                       cfg.EDGE_ELASTICITY)
    edge_top    = objects.StaticObject(edge_size, cfg.SCREEN_WIDTH  / cfg.PIXELS_PER_METER,
                                       cfg.COLORS["BLACK"], cfg.SCREEN_WIDTH / 2, 0,
                                       cfg.EDGE_ELASTICITY)
    edge_right  = objects.StaticObject(cfg.SCREEN_HEIGHT / cfg.PIXELS_PER_METER, edge_size,
                                       cfg.COLORS["BLACK"], cfg.SCREEN_WIDTH,     cfg.SCREEN_HEIGHT / 2,
                                       cfg.EDGE_ELASTICITY)
    edge_bottom = objects.StaticObject(edge_size, cfg.SCREEN_WIDTH  / cfg.PIXELS_PER_METER,
                                       cfg.COLORS["BLACK"], cfg.SCREEN_WIDTH / 2, cfg.SCREEN_HEIGHT,
                                       cfg.EDGE_ELASTICITY)

    static_objects = pygame.sprite.Group()
    for edge in (edge_left, edge_right, edge_top, edge_bottom):
        static_objects.add(edge)

    edges_list = [edge_left, edge_top, edge_right, edge_bottom]

    # -- Default Moving object --
    moving_object = objects.MovingObject(radius=0.25,
                                         color=cfg.COLORS["WHITE"],
                                         pos_x=300,  pos_y=200,
                                         elasticity=1.0,
                                         mass=10)

    moving_objects = pygame.sprite.Group()
    moving_objects.add(moving_object)

    edit_list = [moving_object]

    # -- Subsystems --
    mouse     = mymouse.Mouse()
    edit_menu = ui.EditMenu()
    trail     = objects.TrailSystem(max_points=8000)
    
    # Close button
    close_button = CloseButton(5, 5, 220, 40)

    # -- Simulation state --
    simulation_started = True
    simulation_paused  = False

    physics_timestep = 1.0 / cfg.PHYSICS_FPS
    accumulator = 0.0
    last_time = time.perf_counter()

    fps_counter = 0
    fps_timer = time.time()
    current_fps = 0

    # -- Local helpers --

    def reset_simulation():
        # reset speed
        # reset trail
        for obj in moving_objects:
            obj.reset_speed()
            obj.sync_logical_to_visual()
        trail.clear()

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
            
            # close button takes priority
            if close_button.handle_event(event):
                print("Returning to main menu...")
                run = False
                continue

            # edit menu takes priority
            menu_result = edit_menu.handle_event(event)

            if edit_menu.menu_mode == "settings" and menu_result == "apply_changes":
                old_mode = cfg.get("COLLISION_MODE", "2D")
                accumulator = 0.0
                
                # update edge elasticity for all walls
                for edge in edges_list:
                    edge.elasticity = cfg.EDGE_ELASTICITY
                
                # update gravity force for all moving objects
                for obj in moving_objects:
                    obj.gforce = [0.0, obj.mass * cfg.GRAVITY]
                
                # handle mode switching
                new_mode = cfg.COLLISION_MODE
                if old_mode != new_mode:
                    print(f"Switching from {old_mode} to {new_mode} mode")
                    
                    if new_mode == "1D":
                        # place all objects on the track
                        for obj in moving_objects:
                            obj.set_center((obj.pos_x, TRACK_Y))
                            obj.set_velocity_y(0.0)
                            obj.sync_logical_to_visual()
                        print("Objects placed on 1D track")
                
                continue

            if menu_result:
                continue

            # -- Right-click -> open edit menu --
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                mouse_pos      = pygame.mouse.get_pos()
                object_clicked = False
                for obj in edit_list:
                    if obj.click_hitbox.collidepoint(mouse_pos):
                        edit_menu.show(obj)
                        object_clicked = True
                        break
                if not object_clicked:
                    edit_menu.show()

            # -- Keyboard --
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    edit_menu.hide()
                if event.key == pygame.K_f:
                    simulation_started = not simulation_started
                    simulation_paused = not simulation_paused
                if event.key == pygame.K_r:
                    reset_simulation()
                
                if event.key == pygame.K_a:
                    
                    if len(moving_objects) >= 3:
                        print("Cannot add more than 3 moving objects")
                        continue

                    mx, my = mouse.get_mouse_pos()
                    new_object = objects.MovingObject(
                        radius=0.25,
                        color=cfg.COLORS["WHITE"],
                        pos_x=mx, pos_y=my,
                        elasticity=1.0,
                        mass=10
                    )
                    moving_objects.add(new_object)
                    edit_list.append(new_object)
                    print(f"Added moving object at ({mx}, {my})")
                
                if event.key == pygame.K_s:
                    mouse_pos = mouse.get_mouse_pos()
                    object_to_delete = None
                    for obj in edit_list:
                        if obj.click_hitbox.collidepoint(mouse_pos):
                            object_to_delete = obj
                            break
                    
                    if object_to_delete and len(list(moving_objects)) > 1:
                        moving_objects.remove(object_to_delete)
                        edit_list.remove(object_to_delete)
                        print(f"Deleted moving object")
                    elif object_to_delete and len(list(moving_objects)) == 1:
                        print("Cannot delete the last moving object")
                        continue

        # -- Drag-and-drop --
        if mouse.is_lmb_clicked() and simulation_paused:
            mouse_pos = mouse.get_mouse_pos()
            if mouse.draggable_object is None:
                for obj in edit_list:
                    if obj.click_hitbox.collidepoint(mouse_pos):
                        mouse.draggable_object    = obj
                        break
            else:
                mouse.draggable_object.set_center(mouse_pos)

        elif not mouse.is_lmb_clicked() and simulation_paused:
            if mouse.draggable_object is not None:
                mouse.draggable_object.sync_logical_to_visual()
            mouse.draggable_object    = None
            mouse.draggable_object_id = None

        # -- Physics (fixed timestep) --
        physics_steps = 0
        while accumulator >= physics_timestep and physics_steps < 10:

            # Step 1: detect and resolve wall contacts (only for non-stopped objects)
            wall_collisions = collisions.check_wall_collisions(moving_objects, edges_list)
            if wall_collisions:
                collisions.resolve_wall_collisions(wall_collisions)

            # Step 2: apply forces (only to non-stopped objects)
            for obj in moving_objects:
                obj.acceleration_x = 0.0
                obj.acceleration_y = 0.0
                
                # Only apply gravity in 2D mode
                if cfg.COLLISION_MODE == "2D":
                    obj.resolve_forces(obj.get_gforce())

            # Step 3: integrate positions and velocities (only for non-stopped objects)
            for obj in moving_objects:
                obj.update_physics(physics_timestep)

            # Step 4: ball–ball collisions (after new positions, only active objects)
            circle_collisions = collisions.check_circle_collisions(moving_objects)
            if circle_collisions:
                collisions.resolve_circle_collisions(circle_collisions, elasticity=cfg.COLLISION_ELASTICITY)
            
            # Step 5: check total energy and stop objects with insufficient energy
            if cfg.COLLISION_MODE == "2D":
                ground_y = GROUND_SURFACE_Y  # Top surface of ground edge

                all_objects_stopped = True
                for obj in moving_objects:
                    # default threshold: 0.02m = 2cm equivalent height
                    if obj.check_should_stop(ground_y, threshold_height=0.02):
                        # stop the object if no rebound
                        obj.velocity_x = 0
                        obj.velocity_y = 0

                    else:
                        all_objects_stopped = False

                if all_objects_stopped:
                    simulation_started = not simulation_started
                    simulation_paused = not simulation_paused

            accumulator   -= physics_timestep
            physics_steps += 1

        # -- Trail --
        if not simulation_paused:
            for obj in moving_objects:
                trail.add_point(obj.get_center())

        # -- Rendering --
        screen.fill(cfg.COLORS["WHITE"])

        #static_objects.draw(screen)
        trail.draw(screen)

        # edge outlines + outward normals (debug)
        for static_obj in edges_list:
            static_obj.draw(screen)
            for p1, p2 in static_obj.edges:
                pygame.draw.line(screen, (255, 0, 255),
                                 (int(p1[0]), int(p1[1])),
                                 (int(p2[0]), int(p2[1])), 2)
                mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                nx, ny = collisions.get_line_normal(p1, p2)
                pygame.draw.line(screen, (0, 255, 0),
                                 (int(mx), int(my)),
                                 (int(mx + nx * 30), int(my + ny * 30)), 2)

        # draw moving object overlays: centre dot, velocity arrow, hitbox
        for obj in moving_objects:
            center       = obj.get_center()
            vel_x, vel_y = obj.get_velocity_x(), obj.get_velocity_y()

            obj.draw(screen)
            pygame.draw.circle(screen, (0, 0, 255),
                               (int(center[0]), int(center[1])), 5)
            pygame.draw.line(screen, (0, 0, 255),
                             center,
                             (center[0] + vel_x * 10, center[1] + vel_y * 10), 2)
            pygame.draw.rect(screen, cfg.COLORS["GREEN"], obj.click_hitbox, 1)

        edit_menu.draw(screen)
        
        # Close button
        close_button.draw(screen)

        # -- HUD --
        font      = pygame.font.Font(None, 24)
        sim_state = "PAUSED" if simulation_paused else "RUNNING"
        
        # calculate total mechanical energy (KE + GPE) for all objects
        
        ground_y = GROUND_SURFACE_Y  # use actual ground surface position
            
        hud_moving_object_lines = []

        for obj in moving_objects:
            hud_moving_object_lines.append("")
            hud_moving_object_lines.append(f"Ball velocity: ({obj.get_velocity_x():.2f}, {obj.get_velocity_y():.2f}) m/s")
            hud_moving_object_lines.append(f"Ball mass: {obj.mass} kg",)

            # total kinetic energy
            ke = 0.5 * obj.mass * (obj.velocity_y**2 + obj.velocity_x**2)
            # gravitational potential energy (relative to ground)
            radius_px = obj.radius * cfg.PIXELS_PER_METER
            ball_bottom_y = obj.pos_y + radius_px
            height_m = (ground_y - ball_bottom_y) / cfg.PIXELS_PER_METER
            gpe = obj.mass * cfg.GRAVITY * height_m

            hud_moving_object_lines.append(f"Height: {height_m:.3f} m")
            hud_moving_object_lines.append(f"Total KE: {ke:.3f} J")
            hud_moving_object_lines.append(f"Total GPE: {gpe:.3f} J")
        
        hud_lines = [
            f"Graphics FPS: {current_fps}/{cfg.FPS}",
            f"Physics FPS: {cfg.PHYSICS_FPS}",
            f"Time Scale: {cfg.TIME_SCALE}x",
            f"Simulation: {sim_state}",
        ]
        hud_lines += hud_moving_object_lines

        for i, text in enumerate(hud_lines):
            surf = font.render(text, True, cfg.COLORS["GREEN"])
            screen.blit(surf, (edge_size/2*cfg.PIXELS_PER_METER + 10, edge_size/2*cfg.PIXELS_PER_METER + 10 + i * 25))

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