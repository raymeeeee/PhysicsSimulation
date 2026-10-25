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
import strings
import ui

pygame.init()

# -- Close Button --
class CloseButton:
    
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.hovered = False
        self.font = pygame.font.Font(None, 24)
        
        # -- Colors --
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
    pygame.display.set_caption("String Simulation")
    clock  = pygame.time.Clock()

    # -- Scene objects --
    # default moving object
    radius = 0.25
    moving_object = objects.MovingObject(
        radius=radius,
        color=cfg.COLORS["WHITE"],
        pos_x=cfg.SCREEN_WIDTH  / 2,
        pos_y=cfg.SCREEN_HEIGHT / 2,
        mass=10,
    )

    moving_objects = pygame.sprite.Group()
    moving_objects.add(moving_object)

    # -- Strings --
    # default string 1 meter abouve the moving object
    base_string  = strings.String(
        start_x=cfg.SCREEN_WIDTH  / 2,
        start_y=cfg.SCREEN_HEIGHT / 2 - 1*cfg.PIXELS_PER_METER,
        elasticity_modulus=150,
        natural_length=4,
        particle=moving_object,
    )
    string_objects = [base_string]

    # -- Edit list (objects pickable by right-click or drag) --
    edit_list = [moving_object, base_string]

    # -- Subsystems --
    mouse = mymouse.Mouse()
    edit_menu = ui.EditMenu()
    trail = objects.TrailSystem(max_points=8000)

    # Close button
    close_button = CloseButton(10, 10, 220, 40)

    # -- Simulation state --
    simulation_started = True
    simulation_paused = False

    physics_timestep = 1.0 / cfg.PHYSICS_FPS
    accumulator = 0.0
    last_time = time.perf_counter()

    fps_counter = 0
    fps_timer = time.time()
    current_fps = 0

    # -- Camera state --
    camera_panning = False
    camera_pan_start = (0, 0)

    # -- Main loop --

    run = True
    while run:

        # -- Timing --
        current_time = time.perf_counter()
        dt           = current_time - last_time
        last_time    = current_time

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
            if edit_menu.menu_mode == "settings" and menu_result == "apply_changes":
                accumulator = 0.0
                continue
            if menu_result:
                continue

            # -- Camera pan: start / stop --
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (2, 3):
                camera_panning = True
                camera_pan_start = pygame.mouse.get_pos()
            if event.type == pygame.MOUSEBUTTONUP and event.button in (2, 3):
                camera_panning = False

            # -- Zoom --
            if event.type == pygame.MOUSEWHEEL:
                zoom_center_x, zoom_center_y = pygame.mouse.get_pos()
                old_ppm = cfg.PIXELS_PER_METER

                cfg.PIXELS_PER_METER = max(20, min(200, cfg.PIXELS_PER_METER + event.y * 5))
                zoom_ratio = cfg.PIXELS_PER_METER / old_ppm

                # Reposition moving object around zoom center
                # Calculate current visual position
                old_vx = moving_object.logical_x * old_ppm + moving_object.camera_offset_x
                old_vy = moving_object.logical_y * old_ppm + moving_object.camera_offset_y
                
                # Scale position relative to zoom center
                new_vx = zoom_center_x + (old_vx - zoom_center_x) * zoom_ratio
                new_vy = zoom_center_y + (old_vy - zoom_center_y) * zoom_ratio
                
                # Update camera offset to maintain logical position
                moving_object.camera_offset_x = new_vx - moving_object.logical_x * cfg.PIXELS_PER_METER
                moving_object.camera_offset_y = new_vy - moving_object.logical_y * cfg.PIXELS_PER_METER
                
                # Update visual position
                moving_object.pos_x = new_vx
                moving_object.pos_y = new_vy
                moving_object.rect.center = (new_vx, new_vy)
                moving_object.click_hitbox = moving_object._make_hitbox()

                # Reposition each string anchor around zoom center
                for s in string_objects:
                    old_sx = s.logical_start_x * old_ppm + s.camera_offset_x
                    old_sy = s.logical_start_y * old_ppm + s.camera_offset_y
                    
                    new_sx = zoom_center_x + (old_sx - zoom_center_x) * zoom_ratio
                    new_sy = zoom_center_y + (old_sy - zoom_center_y) * zoom_ratio
                    
                    s.camera_offset_x = new_sx - s.logical_start_x * cfg.PIXELS_PER_METER
                    s.camera_offset_y = new_sy - s.logical_start_y * cfg.PIXELS_PER_METER
                    
                    s.start_x = new_sx
                    s.start_y = new_sy
                    s.click_hitbox = s._make_hitbox()

                trail.scale_points((zoom_center_x, zoom_center_y), zoom_ratio)

            # -- Right-click → open edit menu --
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

                # -- Exit simulation --

                if event.key == pygame.K_ESCAPE:
                    edit_menu.hide()

                # -- Pause simulation --

                if event.key == pygame.K_f:
                    simulation_paused = not simulation_paused
                    simulation_started = not simulation_started

                # -- Reset simulation --

                if event.key == pygame.K_r:
                    # Reset to one object + one string, move camera to be on top of the moving object
                    moving_object.reset_speed()
                    trail.clear()
                    moving_object.distance_travelled = 0
                    
                    # center camera on the moving object
                    screen_center_x = cfg.SCREEN_WIDTH / 2
                    screen_center_y = cfg.SCREEN_HEIGHT / 2
                    # calculate current visual position of object
                    current_visual_x = moving_object.pos_x
                    current_visual_y = moving_object.pos_y
                    # calculate offset needed to center object on screen
                    dx = screen_center_x - current_visual_x
                    dy = screen_center_y - current_visual_y
                    # apply offset to moving object
                    moving_object.apply_camera_offset(dx, dy)
                    # apply offset to all strings
                    for s in string_objects:
                        s.apply_camera_offset(dx, dy)
                    # apply offset to trail
                    trail.translate_points(dx, dy)

                # -- Add string --

                if event.key == pygame.K_a:

                    if len(string_objects) >= 3:
                        print("Cannot add more than 3 string objects")
                        continue

                    mx, my = mouse.get_mouse_pos()
                    new_string = strings.String(
                        start_x=mx, start_y=my,
                        elasticity_modulus=150, natural_length=4,
                        particle=moving_object,
                    )

                    new_string.camera_offset_x = moving_object.camera_offset_x
                    new_string.camera_offset_y = moving_object.camera_offset_y
                    # recalculate logical position with proper camera offset
                    new_string.logical_start_x = (mx - new_string.camera_offset_x) / cfg.PIXELS_PER_METER
                    new_string.logical_start_y = (my - new_string.camera_offset_y) / cfg.PIXELS_PER_METER
                    # update hitbox with new position
                    new_string.click_hitbox = new_string._make_hitbox()
                    
                    string_objects.append(new_string)
                    edit_list.append(new_string)
                    print(f"Added string at ({mx}, {my})")

                # -- Delete string --

                if event.key == pygame.K_s:

                    mouse_pos = mouse.get_mouse_pos()
                    string_to_delete = None
                    for s in string_objects:
                        if s.click_hitbox.collidepoint(mouse_pos):
                            string_to_delete = s
                            break
                    
                    if string_to_delete and len(string_objects) > 1:
                        string_objects.remove(string_to_delete)
                        edit_list.remove(string_to_delete)
                        print(f"Deleted string")

                    elif len(string_objects) <= 1:
                        print("Cannot delete the last string object")
                        continue

        # -- Camera panning (every frame while held) --
        if camera_panning and mouse.draggable_object is None:
            cur = pygame.mouse.get_pos()
            dx  = cur[0] - camera_pan_start[0]
            dy  = cur[1] - camera_pan_start[1]

            moving_object.apply_camera_offset(dx, dy)
            for s in string_objects:
                s.apply_camera_offset(dx, dy)
            trail.translate_points(dx, dy)

            camera_pan_start = cur  

        # -- Drag-and-drop --
        if mouse.is_lmb_clicked() and simulation_paused:
            mouse_pos = mouse.get_mouse_pos()

            if mouse.draggable_object is None:
                for obj in edit_list:
                    if obj.click_hitbox.collidepoint(mouse_pos):
                        mouse.draggable_object = obj
                        break
            else:
                mouse.draggable_object.set_center(mouse_pos)

        elif not mouse.is_lmb_clicked() and simulation_paused:
            if mouse.draggable_object is not None:
                mouse.draggable_object.sync_logical_to_visual()
            mouse.draggable_object = None

        # -- Physics --
        physics_steps = 0
        while accumulator >= physics_timestep and physics_steps < 10:
            if simulation_started and not simulation_paused:
                forces = [s.calculate_tension() for s in string_objects]
                forces.append(moving_object.get_gforce())
                moving_object.resolve_forces(*forces)
                moving_object.update_physics(physics_timestep)
            accumulator   -= physics_timestep
            physics_steps += 1

        # -- Trail --
        if simulation_started and not simulation_paused:
            trail.add_point(moving_object.get_center())

        # -- Rendering --
        screen.fill(cfg.COLORS["WHITE"])

        trail.draw(screen)

        for s in string_objects:
            s.draw(screen)

        moving_object.draw(screen)

        # Click hitboxes (debug)
        for obj in edit_list:
            pygame.draw.rect(screen, cfg.COLORS["BLACK"], obj.click_hitbox, 1)

        # Velocity arrow
        center = moving_object.get_center()
        vel_x, vel_y = moving_object.get_velocity_x(), moving_object.get_velocity_y()
        pygame.draw.circle(screen, (0, 0, 255), (int(center[0]), int(center[1])), 5)
        pygame.draw.line(screen, (0, 0, 255),
                         center,
                         (center[0] + vel_x * 10, center[1] + vel_y * 10), 2)

        # Edit menu
        edit_menu.draw(screen)

        # Close button
        close_button.draw(screen)

        # -- HUD --
        font = pygame.font.Font(None, 24)
        sim_state = "RUNNING" if simulation_started and not simulation_paused else "PAUSED"
        hud_lines = [
            f"Graphics FPS: {current_fps}/{cfg.FPS}",
            f"Physics FPS: {cfg.PHYSICS_FPS}",
            f"Velocity X: {vel_x:.2f} m/s",
            f"Velocity Y: {vel_y:.2f} m/s",
            f"Acceleration X: {moving_object.get_acceleration_x():.2f} m/s²",
            f"Acceleration Y: {moving_object.get_acceleration_y():.2f} m/s²",
            f"Mass: {moving_object.get_mass()} kg",
            f"Time Scale: {cfg.TIME_SCALE}x",
            f"Simulation: {sim_state}",
            #f"Trail points: {trail.length()}",
            f"Distance travelled: {moving_object.distance_travelled:.3f} m",
            
        ]
        hud_lines.append("")
        for s in string_objects:
            t = s.calculate_tension()
            hud_lines.append(f"Tension: {math.hypot(t[0], t[1]):.3f} N") # takes magnitude of tension
            hud_lines.append(f"Extension: {(s.calculate_extension()):.3f} m")
            hud_lines.append(f"EPE: {(s.calcualte_elastic_potential_energy()):.3f} J")
            hud_lines.append("")

        for i, line in enumerate(hud_lines):
            surf = font.render(line, True, cfg.COLORS["GREEN"])
            screen.blit(surf, (10, 60 + i * 25))

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