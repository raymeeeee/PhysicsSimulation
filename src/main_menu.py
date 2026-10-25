import pygame
import sys
import subprocess
import pathlib
from config_manager import get_config_manager


class Button:
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        
        self.bg_color = [98, 114, 164]
        self.hover_color = [139, 157, 195]
        self.text_color = [248, 248, 242]
        
        self.font = pygame.font.Font(None, 32)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                self.callback()
                return True
        return False
    
    def draw(self, screen):
        color = self.hover_color if self.hovered else self.bg_color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, self.text_color, self.rect, 2, border_radius=8)
        
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


class SettingsPanel:
    
    def __init__(self, menu=None):
        self.cfg = get_config_manager() 
        self.visible = False
        self.menu = menu  # reference to main menu for restart
        
        self.width = 330
        self.padding = 20
        
        self.title_font = pygame.font.Font(None, 36)
        self.label_font = pygame.font.Font(None, 24)
        self.input_font = pygame.font.Font(None, 22)
        
        self.bg_color = [40, 42, 54]
        self.text_color = [248, 248, 242]
        self.input_bg = [68, 71, 90]
        self.input_active = [98, 114, 164]
        self.border_color = [98, 114, 164]
        
        self.fields = []
        self.active_field = None
        self.close_button = None
        self.save_button = None
        
        self.update_position()
    
    def update_position(self):
        screen_w = self.cfg.SCREEN_WIDTH
        screen_h = self.cfg.SCREEN_HEIGHT
        
        self.x = screen_w - self.width
        self.y = 0
        self.height = screen_h
        
        # setup fields
        self.fields = []
        y = 100
        spacing = 80
        
        sections = [
            ("Display", [
                ("fps", "Graphics FPS", self.cfg.FPS),
                ("physics_fps", "Physics FPS", self.cfg.PHYSICS_FPS),
            ]),
            ("Physics", [
                ("gravity", "Gravity (m/s²)", self.cfg.GRAVITY),
            ]),
        ]
        
        for section_name, section_fields in sections:
            self.fields.append({
                'type': 'header',
                'label': section_name,
                'y': y,
            })
            y += 40
            
            for name, label, value in section_fields:
                self.fields.append({
                    'type': 'input',
                    'name': name,
                    'label': label,
                    'value': str(value),
                    'y': y,
                })
                y += spacing
        
        # buttons
        button_y = self.height - 120
        button_w = (self.width - 3 * self.padding) // 2
        
        self.save_button = Button(
            self.x + self.padding,
            button_y,
            button_w,
            50,
            "Save",
            self.save_settings
        )
        
        self.close_button = Button(
            self.x + self.padding * 2 + button_w,
            button_y,
            button_w,
            50,
            "Close",
            self.hide
        )
    
    def show(self):
        self.visible = True
        self.cfg.load()  # reload from disk
        self.update_position()
    
    def hide(self):
        self.visible = False
        self.active_field = None
    
    def save_settings(self):
        try:
            for field in self.fields:
                if field['type'] != 'input':
                    continue
                
                name = field['name']
                value_str = field['value']
                
                # parse value
                if '.' in value_str:
                    value = float(value_str)
                else:
                    value = int(value_str)
                
                # map field names to config paths
                if name in ['fps', 'physics_fps']:
                    self.cfg.set("display", name, value=int(value))
                elif name in ['gravity']:
                    value = 0 if value < 0 else value  # clamp negative to 0
                    self.cfg.set("physics", name, value=value)
            
            if self.cfg.save():
                print("Settings saved successfully!")
                print("Restarting application to apply changes...")
                self.hide()
                # trigger restart of the application
                if self.menu:
                    self.menu.restart_after_save = True
                    self.menu.running = False
        
        except Exception as e:
            print(e)
    
    def get_field_rect(self, field):
        return pygame.Rect(
            self.x + self.padding,
            field['y'] + 30,
            self.width - self.padding * 2,
            35,
        )
    
    def handle_event(self, event):
        if not self.visible:
            return False
        
        # button events
        if self.save_button.handle_event(event) or self.close_button.handle_event(event):
            return True
        
        # field events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active_field = None
            for field in self.fields:
                if field['type'] == 'input':
                    if self.get_field_rect(field).collidepoint(event.pos):
                        self.active_field = field
                        return True
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return True
            
            if self.active_field:
                if event.key == pygame.K_RETURN:
                    self.save_settings()
                elif event.key == pygame.K_BACKSPACE:
                    self.active_field['value'] = self.active_field['value'][:-1]
                elif event.unicode and event.unicode in '0123456789.-':
                    self.active_field['value'] += event.unicode
                return True
        
        return False
    
    def draw(self, screen):
        if not self.visible:
            return
        
        # panel background
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, self.bg_color, panel_rect)
        pygame.draw.rect(screen, self.border_color, panel_rect, 3)
        
        # title
        title_surf = self.title_font.render("Settings", True, self.text_color)
        screen.blit(title_surf,
                   (self.x + (self.width - title_surf.get_width()) // 2, 30))
        
        # display current resolution (non-editable info)
        resolution_text = f"Resolution: {self.cfg.SCREEN_WIDTH}x{self.cfg.SCREEN_HEIGHT}"
        resolution_surf = self.input_font.render(resolution_text, True, self.text_color)
        resolution_x = self.x + (self.width - resolution_surf.get_width()) // 2
        screen.blit(resolution_surf, (resolution_x, 70))
        
        # fields
        for field in self.fields:
            if field['type'] == 'header':
                # section header
                header_surf = self.label_font.render(field['label'], True, self.border_color)
                screen.blit(header_surf, (self.x + self.padding, field['y']))
            
            elif field['type'] == 'input':
                # label
                label_surf = self.label_font.render(field['label'], True, self.text_color)
                screen.blit(label_surf, (self.x + self.padding, field['y']))
                
                # input box
                field_rect = self.get_field_rect(field)
                
                # background color
                bg = self.input_active if field is self.active_field else self.input_bg
                
                pygame.draw.rect(screen, bg, field_rect, border_radius=4)
                pygame.draw.rect(screen, self.border_color, field_rect, 2, border_radius=4)
                
                # text
                text_surf = self.input_font.render(field['value'], True, self.text_color)
                text_x = field_rect.x + 10
                text_y = field_rect.y + (field_rect.height - text_surf.get_height()) // 2
                screen.blit(text_surf, (text_x, text_y))
                
                # cursor
                if field is self.active_field:
                    cursor_x = text_x + text_surf.get_width() + 2
                    pygame.draw.line(screen, self.text_color,
                                   (cursor_x, field_rect.y + 5),
                                   (cursor_x, field_rect.y + field_rect.height - 5), 2)
        
        # save, close buttons
        self.save_button.draw(screen)
        self.close_button.draw(screen)


class MainMenu:
    def __init__(self):
        pygame.init()
        
        self.cfg = get_config_manager()
        self.screen = pygame.display.set_mode((self.cfg.SCREEN_WIDTH, self.cfg.SCREEN_HEIGHT))
        pygame.display.set_caption("Physics Simulations - Main Menu")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.restart_after_sim = False
        self.restart_after_save = False
        self.pending_simulation = None
        
        # fonts
        self.title_font = pygame.font.Font(None, 72)
        self.subtitle_font = pygame.font.Font(None, 32)
        
        # colors
        self.bg_color = self.cfg.COLORS.get("WHITE", (255, 255, 255))
        self.text_color = self.cfg.COLORS.get("BLACK", (0, 0, 0))
        self.accent_color = [98, 114, 164]
        
        # get parent directory for simulations
        self.project_root = pathlib.Path(__file__).resolve().parent
        
        # settings panel (pass self for restart capability)
        self.settings_panel = SettingsPanel(menu=self)
        
        # create buttons
        self.buttons = []
        self.create_buttons()
    
    def create_buttons(self):
        center_x = self.cfg.SCREEN_WIDTH // 2
        start_y = 250
        button_width = 400
        button_height = 60
        spacing = 80
        
        simulations = [
            ("Friction Simulation", "friction_simulation"),
            ("Rebound Simulation", "rebound_simulation"),
            ("String Simulation", "string_simulation"),
        ]
        
        for i, (name, folder) in enumerate(simulations):
            y = start_y + i * spacing
            button = Button(
                center_x - button_width // 2,
                y,
                button_width,
                button_height,
                name,
                lambda f=folder: self.launch_simulation(f)
            )
            self.buttons.append(button)
        
        # settings button
        settings_button = Button(
            center_x - button_width // 2,
            start_y + len(simulations) * spacing,
            button_width,
            button_height,
            "Settings",
            self.settings_panel.show
        )
        self.buttons.append(settings_button)
        
        # exit button
        exit_button = Button(
            center_x - button_width // 2,
            start_y + (len(simulations) + 1) * spacing,
            button_width,
            button_height,
            "Exit",
            self.quit
        )
        self.buttons.append(exit_button)
    
    def launch_simulation(self, sim_folder):
        sim_path = self.project_root / sim_folder / "main.py"
        
        if not sim_path.exists():
            print(f"Simulation not found: {sim_path}")
            return
        
        print(f"Launching {sim_folder}...")
        
        # set flag to restart after simulation
        self.restart_after_sim = True
        self.running = False
        
        # store the simulation path
        self.pending_simulation = sim_path
    
    def quit(self):
        self.running = False
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # settings panel has priority
            if self.settings_panel.handle_event(event):
                continue
            
            # button events
            for button in self.buttons:
                button.handle_event(event)
            
            # keyboard shortcuts
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def draw(self):
        self.screen.fill(self.bg_color)
        
        # title
        title_surf = self.title_font.render("Physics Simulations", True, self.text_color)
        title_rect = title_surf.get_rect(center=(self.cfg.SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_surf, title_rect)
        
        # subtitle
        subtitle_surf = self.subtitle_font.render(
            "Select a simulation to begin", True, self.accent_color
        )
        subtitle_rect = subtitle_surf.get_rect(center=(self.cfg.SCREEN_WIDTH // 2, 160))
        self.screen.blit(subtitle_surf, subtitle_rect)
        
        # buttons
        for button in self.buttons:
            button.draw(self.screen)
        
        # settings panel
        self.settings_panel.draw(self.screen)
        
        pygame.display.flip()
    
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.handle_events()
            self.draw()
            pygame.display.flip()
            clock.tick(60)

        
        pygame.quit()
        
        # return flags for proper restart handling
        return self.restart_after_save, self.pending_simulation


def main():
    while True:
        menu = MainMenu()
        restart, simulation = menu.run()
        
        if restart:
            # restart with new settings
            print("Restarting application with new settings...")
            try:
                subprocess.run([sys.executable] + sys.argv)
            except Exception as e:
                print(f"Error restarting application: {e}")
            break
        elif simulation:
            # run simulation
            print(f"Launching simulation: {simulation}")
            try:
                subprocess.run([sys.executable, str(simulation)])
            except Exception as e:
                print(f"Error running simulation: {e}")
            # continue loop to restart menu after simulation
        else:
            # normal exit
            break


if __name__ == "__main__":
    main()