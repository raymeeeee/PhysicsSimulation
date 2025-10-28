import sys
import math
import json
from pygame.locals import *

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
GRID_SIZE = 20
BACKGROUND_COLOR = (240, 240, 245)
GRID_COLOR = (220, 220, 220)
UI_BACKGROUND = (50, 60, 75)
BUTTON_COLOR = (80, 100, 130)
BUTTON_HOVER_COLOR = (100, 130, 170)
TEXT_COLOR = (240, 240, 240)
HIGHLIGHT_COLOR = (255, 215, 0)
SIMULATION_AREA = (0, 0, 800, 800)

# Create the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Physics Simulation for Further Mathematics")

# Fonts
font_large = pygame.font.SysFont("Arial", 24)
font_medium = pygame.font.SysFont("Arial", 18)
font_small = pygame.font.SysFont("Arial", 14)

class PhysicsObject:
 def __init__(self, x, y, obj_type, radius=20, width=40, height=40):
     self.x = x
     self.y = y
     self.type = obj_type  # "circle", "rectangle", "triangle"
     self.radius = radius
     self.width = width
     self.height = height
     self.color = (70, 130, 180)
     self.mass = 1.0
     self.velocity_x = 0.0
     self.velocity_y = 0.0
     self.elasticity = 0.8
     self.static = False
     self.selected = False
     self.trail = []
     self.max_trail_length = 50
     
 def draw(self, surface):
     # Draw trail
     for i, pos in enumerate(self.trail):
         alpha = int(255 * (i / len(self.trail)))
         color = (self.color[0], self.color[1], self.color[2], alpha)
         pygame.draw.circle(surface, color, pos, 3)
         
     # Draw object
     if self.type == "circle":
         pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
     elif self.type == "rectangle":
         pygame.draw.rect(surface, self.color, (int(self.x - self.width/2), int(self.y - self.height/2), 
                                              self.width, self.height))
     elif self.type == "triangle":
         points = [
             (int(self.x), int(self.y - self.height/2)),
             (int(self.x - self.width/2), int(self.y + self.height/2)),
             (int(self.x + self.width/2), int(self.y + self.height/2))
         ]
         pygame.draw.polygon(surface, self.color, points)
         
     # Draw selection highlight
     if self.selected:
         if self.type == "circle":
             pygame.draw.circle(surface, HIGHLIGHT_COLOR, (int(self.x), int(self.y)), self.radius + 2, 2)
         elif self.type == "rectangle":
             pygame.draw.rect(surface, HIGHLIGHT_COLOR, (int(self.x - self.width/2 - 2), int(self.y - self.height/2 - 2), 
                                                       self.width + 4, self.height + 4), 2)
         elif self.type == "triangle":
             points = [
                 (int(self.x), int(self.y - self.height/2 - 2)),
                 (int(self.x - self.width/2 - 2), int(self.y + self.height/2 + 2)),
                 (int(self.x + self.width/2 + 2), int(self.y + self.height/2 + 2))
             ]
             pygame.draw.polygon(surface, HIGHLIGHT_COLOR, points, 2)
             
     # Draw velocity vector
     if abs(self.velocity_x) > 0.1 or abs(self.velocity_y) > 0.1:
         end_x = self.x + self.velocity_x * 5
         end_y = self.y + self.velocity_y * 5
         pygame.draw.line(surface, (255, 50, 50), (self.x, self.y), (end_x, end_y), 2)
         pygame.draw.circle(surface, (255, 50, 50), (int(end_x), int(end_y)), 4)
 
 def update_trail(self):
     self.trail.append((int(self.x), int(self.y)))
     if len(self.trail) > self.max_trail_length:
         self.trail.pop(0)
 
 def is_point_inside(self, point_x, point_y):
     if self.type == "circle":
         distance = math.sqrt((point_x - self.x)**2 + (point_y - self.y)**2)
         return distance <= self.radius
     elif self.type == "rectangle":
         return (abs(point_x - self.x) <= self.width/2 and 
                 abs(point_y - self.y) <= self.height/2)
     elif self.type == "triangle":
         # Simple triangle point check (for equilateral triangle)
         dx = abs(point_x - self.x)
         dy = point_y - self.y
         return dy >= -self.height/2 and dy <= self.height/2 and dx <= self.width/2 * (1 - (dy + self.height/2) / self.height)
     return False

class Button:
 def __init__(self, x, y, width, height, text, tooltip=""):
     self.rect = pygame.Rect(x, y, width, height)
     self.text = text
     self.tooltip = tooltip
     self.hovered = False
     
 def draw(self, surface):
     color = BUTTON_HOVER_COLOR if self.hovered else BUTTON_COLOR
     pygame.draw.rect(surface, color, self.rect, border_radius=5)
     pygame.draw.rect(surface, (120, 140, 170), self.rect, 2, border_radius=5)
     
     text_surf = font_medium.render(self.text, True, TEXT_COLOR)
     text_rect = text_surf.get_rect(center=self.rect.center)
     surface.blit(text_surf, text_rect)
     
     # Draw tooltip if hovered
     if self.hovered and self.tooltip:
         tooltip_surf = font_small.render(self.tooltip, True, TEXT_COLOR)
         tooltip_rect = tooltip_surf.get_rect(midbottom=(self.rect.centerx, self.rect.top - 5))
         pygame.draw.rect(surface, (40, 50, 60), 
                        (tooltip_rect.x - 5, tooltip_rect.y - 2, tooltip_rect.width + 10, tooltip_rect.height + 4),
                        border_radius=3)
         surface.blit(tooltip_surf, tooltip_rect)
 
 def check_hover(self, pos):
     self.hovered = self.rect.collidepoint(pos)
     return self.hovered
     
 def is_clicked(self, pos, event):
     if event.type == MOUSEBUTTONDOWN and event.button == 1:
         return self.rect.collidepoint(pos)
     return False

class Slider:
 def __init__(self, x, y, width, min_val, max_val, initial_val, label):
     self.rect = pygame.Rect(x, y, width, 20)
     self.min_val = min_val
     self.max_val = max_val
     self.value = initial_val
     self.label = label
     self.dragging = False
     
 def draw(self, surface):
     # Draw slider track
     pygame.draw.rect(surface, (100, 100, 120), (self.rect.x, self.rect.y + 9, self.rect.width, 2))
     
     # Draw slider handle
     handle_pos = self.rect.x + int((self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width)
     pygame.draw.circle(surface, BUTTON_HOVER_COLOR if self.dragging else BUTTON_COLOR, (handle_pos, self.rect.y + 10), 8)
     
     # Draw label and value
     label_text = f"{self.label}: {self.value:.2f}"
     text_surf = font_small.render(label_text, True, TEXT_COLOR)
     surface.blit(text_surf, (self.rect.x, self.rect.y - 20))
     
 def update(self, event, pos):
     if event.type == MOUSEBUTTONDOWN and event.button == 1:
         if pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 20).collidepoint(pos):
             self.dragging = True
             
     if event.type == MOUSEBUTTONUP and event.button == 1:
         self.dragging = False
         
     if self.dragging and event.type == MOUSEMOTION:
         rel_x = max(0, min(pos[0] - self.rect.x, self.rect.width))
         self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
         return True
     return False

class PhysicsSimulation:
 def __init__(self):
     self.objects = []
     self.selected_object = None
     self.dragging = False
     self.drag_offset_x = 0
     self.drag_offset_y = 0
     self.gravity = 0.5
     self.elasticity = 0.8
     self.paused = False
     self.show_grid = True
     self.show_trails = True
     
     # UI elements
     self.buttons = [
         Button(820, 20, 160, 40, "Add Circle", "Add a circular object"),
         Button(820, 70, 160, 40, "Add Rectangle", "Add a rectangular object"),
         Button(820, 120, 160, 40, "Add Triangle", "Add a triangular object"),
         Button(820, 180, 160, 40, "Clear All", "Remove all objects"),
         Button(820, 230, 160, 40, "Pause/Resume", "Pause or resume simulation"),
         Button(820, 280, 160, 40, "Toggle Grid", "Show/hide grid"),
         Button(820, 330, 160, 40, "Toggle Trails", "Show/hide object trails"),
         Button(820, 390, 160, 40, "Save Simulation", "Save current simulation to file"),
         Button(820, 440, 160, 40, "Load Simulation", "Load simulation from file")
     ]
     
     self.sliders = [
         Slider(820, 520, 350, 0.0, 2.0, 0.5, "Gravity"),
         Slider(820, 570, 350, 0.0, 1.0, 0.8, "Elasticity"),
         Slider(820, 620, 350, 0.1, 2.0, 1.0, "Simulation Speed")
     ]
     
     self.simulation_speed = 1.0
     
 def add_object(self, obj_type):
     new_obj = PhysicsObject(400, 300, obj_type)
     self.objects.append(new_obj)
     return new_obj
     
 def draw(self, surface):
     # Draw simulation background
     pygame.draw.rect(surface, BACKGROUND_COLOR, SIMULATION_AREA)
     
     # Draw grid
     if self.show_grid:
         for x in range(0, SIMULATION_AREA[2], GRID_SIZE):
             pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, SIMULATION_AREA[3]))
         for y in range(0, SIMULATION_AREA[3], GRID_SIZE):
             pygame.draw.line(surface, GRID_COLOR, (0, y), (SIMULATION_AREA[2], y))
             
     # Draw objects
     for obj in self.objects:
         if self.show_trails:
             obj.update_trail()
         obj.draw(surface)
         
     # Draw UI background
     pygame.draw.rect(surface, UI_BACKGROUND, (800, 0, 400, 800))
     
     # Draw title
     #title_text = font_large.render("Physics Simulation", True, TEXT_COLOR)
     #surface.blit(title_text, (820, 750))
     
     # Draw UI elements
     for button in self.buttons:
         button.draw(surface)
         
     for slider in self.sliders:
         slider.draw(surface)
         
     # Draw stats
     stats_text = [
         f"Objects: {len(self.objects)}",
         f"Gravity: {self.gravity:.2f}",
         f"Elasticity: {self.elasticity:.2f}",
         f"Status: {'Paused' if self.paused else 'Running'}"
     ]
     
     for i, text in enumerate(stats_text):
         text_surf = font_small.render(text, True, TEXT_COLOR)
         surface.blit(text_surf, (1000, 680 + i*25))
         
     # Draw instructions
     instructions = [
         "Left click: Select object",
         "Right click: Drag object",
         "Mouse wheel: Adjust object size",
         "Delete key: Remove selected object"
     ]
     
     for i, text in enumerate(instructions):
         text_surf = font_small.render(text, True, TEXT_COLOR)
         surface.blit(text_surf, (820, 680 + i*25))
 
 def update(self):
     if self.paused:
         return
         
     # Update physics for all objects
     for obj in self.objects:
         if obj.static:
             continue
             
         # Apply gravity
         obj.velocity_y += self.gravity * self.simulation_speed
         
         # Update position
         obj.x += obj.velocity_x * self.simulation_speed
         obj.y += obj.velocity_y * self.simulation_speed
         
         # Boundary collision
         if obj.type == "circle":
             if obj.x - obj.radius < 0:
                 obj.x = obj.radius
                 obj.velocity_x = -obj.velocity_x * self.elasticity
             elif obj.x + obj.radius > SIMULATION_AREA[2]:
                 obj.x = SIMULATION_AREA[2] - obj.radius
                 obj.velocity_x = -obj.velocity_x * self.elasticity
                 
             if obj.y - obj.radius < 0:
                 obj.y = obj.radius
                 obj.velocity_y = -obj.velocity_y * self.elasticity
             elif obj.y + obj.radius > SIMULATION_AREA[3]:
                 obj.y = SIMULATION_AREA[3] - obj.radius
                 obj.velocity_y = -obj.velocity_y * self.elasticity
                 
         elif obj.type == "rectangle":
             if obj.x - obj.width/2 < 0:
                 obj.x = obj.width/2
                 obj.velocity_x = -obj.velocity_x * self.elasticity
             elif obj.x + obj.width/2 > SIMULATION_AREA[2]:
                 obj.x = SIMULATION_AREA[2] - obj.width/2
                 obj.velocity_x = -obj.velocity_x * self.elasticity
                 
             if obj.y - obj.height/2 < 0:
                 obj.y = obj.height/2
                 obj.velocity_y = -obj.velocity_y * self.elasticity
             elif obj.y + obj.height/2 > SIMULATION_AREA[3]:
                 obj.y = SIMULATION_AREA[3] - obj.height/2
                 obj.velocity_y = -obj.velocity_y * self.elasticity
                 
         elif obj.type == "triangle":
             if obj.x - obj.width/2 < 0:
                 obj.x = obj.width/2
                 obj.velocity_x = -obj.velocity_x * self.elasticity
             elif obj.x + obj.width/2 > SIMULATION_AREA[2]:
                 obj.x = SIMULATION_AREA[2] - obj.width/2
                 obj.velocity_x = -obj.velocity_x * self.elasticity
                 
             if obj.y - obj.height/2 < 0:
                 obj.y = obj.height/2
                 obj.velocity_y = -obj.velocity_y * self.elasticity
             elif obj.y + obj.height/2 > SIMULATION_AREA[3]:
                 obj.y = SIMULATION_AREA[3] - obj.height/2
                 obj.velocity_y = -obj.velocity_y * self.elasticity
         
         # Apply some damping
         obj.velocity_x *= 0.99
         obj.velocity_y *= 0.99
         
     # Simple collision detection between objects
     for i in range(len(self.objects)):
         for j in range(i+1, len(self.objects)):
             obj1 = self.objects[i]
             obj2 = self.objects[j]
             
             if obj1.static and obj2.static:
                 continue
                 
             # Circle-circle collision
             if obj1.type == "circle" and obj2.type == "circle":
                 dx = obj2.x - obj1.x
                 dy = obj2.y - obj1.y
                 distance = math.sqrt(dx*dx + dy*dy)
                 
                 if distance < obj1.radius + obj2.radius:
                     # Calculate collision response
                     angle = math.atan2(dy, dx)
                     
                     # Move objects apart
                     overlap = (obj1.radius + obj2.radius - distance) / 2.0
                     obj1.x -= overlap * math.cos(angle)
                     obj1.y -= overlap * math.sin(angle)
                     obj2.x += overlap * math.cos(angle)
                     obj2.y += overlap * math.sin(angle)
                     
                     # Calculate new velocities
                     total_mass = obj1.mass + obj2.mass
                     
                     v1x = obj1.velocity_x
                     v1y = obj1.velocity_y
                     v2x = obj2.velocity_x
                     v2y = obj2.velocity_y
                     
                     obj1.velocity_x = (v1x*(obj1.mass - obj2.mass) + 2*obj2.mass*v2x) / total_mass * self.elasticity
                     obj1.velocity_y = (v1y*(obj1.mass - obj2.mass) + 2*obj2.mass*v2y) / total_mass * self.elasticity
                     obj2.velocity_x = (v2x*(obj2.mass - obj1.mass) + 2*obj1.mass*v1x) / total_mass * self.elasticity
                     obj2.velocity_y = (v2y*(obj2.mass - obj1.mass) + 2*obj1.mass*v1y) / total_mass * self.elasticity
 
 def handle_event(self, event):
     mouse_pos = pygame.mouse.get_pos()
     
     # Update button hover states
     for button in self.buttons:
         button.check_hover(mouse_pos)
         
     # Update sliders
     for slider in self.sliders:
         if slider.update(event, mouse_pos):
             if slider.label == "Gravity":
                 self.gravity = slider.value
             elif slider.label == "Elasticity":
                 self.elasticity = slider.value
             elif slider.label == "Simulation Speed":
                 self.simulation_speed = slider.value
     
     # Handle button clicks
     if event.type == MOUSEBUTTONDOWN:
         if event.button == 1:  # Left click
             # Check if clicked on a button
             for i, button in enumerate(self.buttons):
                 if button.is_clicked(mouse_pos, event):
                     if i == 0:  # Add Circle
                         self.add_object("circle")
                     elif i == 1:  # Add Rectangle
                         self.add_object("rectangle")
                     elif i == 2:  # Add Triangle
                         self.add_object("triangle")
                     elif i == 3:  # Clear All
                         self.objects.clear()
                         self.selected_object = None
                     elif i == 4:  # Pause/Resume
                         self.paused = not self.paused
                     elif i == 5:  # Toggle Grid
                         self.show_grid = not self.show_grid
                     elif i == 6:  # Toggle Trails
                         self.show_trails = not self.show_trails
                     elif i == 7:  # Save Simulation
                         self.save_simulation()
                     elif i == 8:  # Load Simulation
                         self.load_simulation()
                     return
             
             # Check if clicked on an object
             if mouse_pos[0] < SIMULATION_AREA[2]:
                 self.selected_object = None
                 for obj in self.objects:
                     if obj.is_point_inside(mouse_pos[0], mouse_pos[1]):
                         self.selected_object = obj
                         obj.selected = True
                     else:
                         obj.selected = False
                         
         elif event.button == 3:  # Right click
             if mouse_pos[0] < SIMULATION_AREA[2]:
                 for obj in self.objects:
                     if obj.is_point_inside(mouse_pos[0], mouse_pos[1]):
                         self.dragging = True
                         self.drag_offset_x = obj.x - mouse_pos[0]
                         self.drag_offset_y = obj.y - mouse_pos[1]
                         break
                     
         elif event.button == 4:  # Mouse wheel up
             if self.selected_object:
                 if self.selected_object.type == "circle":
                     self.selected_object.radius = max(5, self.selected_object.radius + 2)
                 else:
                     self.selected_object.width = max(10, self.selected_object.width + 4)
                     self.selected_object.height = max(10, self.selected_object.height + 4)
                     
         elif event.button == 5:  # Mouse wheel down
             if self.selected_object:
                 if self.selected_object.type == "circle":
                     self.selected_object.radius = max(5, self.selected_object.radius - 2)
                 else:
                     self.selected_object.width = max(10, self.selected_object.width - 4)
                     self.selected_object.height = max(10, self.selected_object.height - 4)
                     
     elif event.type == MOUSEBUTTONUP:
         if event.button == 3:  # Right click release
             self.dragging = False
             
     elif event.type == MOUSEMOTION:
         if self.dragging and mouse_pos[0] < SIMULATION_AREA[2]:
             for obj in self.objects:
                 if obj.is_point_inside(mouse_pos[0] + self.drag_offset_x, 
                                      mouse_pos[1] + self.drag_offset_y):
                     obj.x = mouse_pos[0] + self.drag_offset_x
                     obj.y = mouse_pos[1] + self.drag_offset_y
                     # Reset velocity when dragging
                     obj.velocity_x = 0
                     obj.velocity_y = 0
                     break
                     
     elif event.type == KEYDOWN:
         if event.key == K_DELETE and self.selected_object:
             self.objects.remove(self.selected_object)
             self.selected_object = None
             
 def save_simulation(self):
     # Create a data structure to save
     data = {
         "gravity": self.gravity,
         "elasticity": self.elasticity,
         "objects": []
     }
     
     for obj in self.objects:
         obj_data = {
             "type": obj.type,
             "x": obj.x,
             "y": obj.y,
             "radius": obj.radius,
             "width": obj.width,
             "height": obj.height,
             "mass": obj.mass,
             "color": obj.color,
             "static": obj.static,
             "elasticity": obj.elasticity
         }
         data["objects"].append(obj_data)
         
     # Save to a JSON file
     with open("simulation.json", "w") as f:
         json.dump(data, f)
         
     print("Simulation saved to simulation.json")
     
 def load_simulation(self):
     try:
         with open("simulation.json", "r") as f:
             data = json.load(f)
             
         # Load simulation parameters
         self.gravity = data["gravity"]
         self.elasticity = data["elasticity"]
         
         # Load objects
         self.objects = []
         for obj_data in data["objects"]:
             obj = PhysicsObject(obj_data["x"], obj_data["y"], obj_data["type"])
             obj.radius = obj_data["radius"]
             obj.width = obj_data["width"]
             obj.height = obj_data["height"]
             obj.mass = obj_data["mass"]
             obj.color = tuple(obj_data["color"])
             obj.static = obj_data["static"]
             obj.elasticity = obj_data["elasticity"]
             self.objects.append(obj)
             
         # Update sliders
         for slider in self.sliders:
             if slider.label == "Gravity":
                 slider.value = self.gravity
             elif slider.label == "Elasticity":
                 slider.value = self.elasticity
                 
         print("Simulation loaded from simulation.json")
         
     except FileNotFoundError:
         print("No saved simulation found")

# Main game loop
def main():
 clock = pygame.time.Clock()
 simulation = PhysicsSimulation()
 
 # Add some initial objects
 circle = simulation.add_object("circle")
 circle.x, circle.y = 200, 200
 circle.velocity_x = 2
 
 rect = simulation.add_object("rectangle")
 rect.x, rect.y = 600, 400
 rect.velocity_y = -1
 
 triangle = simulation.add_object("triangle")
 triangle.x, triangle.y = 400, 600
 
 running = True
 while running:
     for event in pygame.event.get():
         if event.type == QUIT:
             running = False
         simulation.handle_event(event)
             
     simulation.update()
     screen.fill((0, 0, 0))
     simulation.draw(screen)
     
     pygame.display.flip()
     clock.tick(60)
     
 pygame.quit()
 sys.exit()

if __name__ == "__main__":
 main()

