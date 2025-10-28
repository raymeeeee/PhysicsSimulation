import pygame
#import pygame.gfxdraw
import sys
import math
import json
from pygame.locals import *
import time
#from multipledispatch import dispatch

#config.py
import config as cfg

pygame.init()



screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
pygame.display.set_caption("Simulation")



class Entity(pygame.sprite.Sprite):
    entity_id = 0 #instances counter
    
    def __init__(self, height, width):
        pygame.sprite.Sprite.__init__(self)
        self.height = height
        self.width = width
        Entity.entity_id += 1
        self.entity_id = Entity.entity_id
    
    def GetId(self): return self.entity_id
    def GetHeight(self): return self.height
    def GetWidth(self): return self.width
    
class StaticObject(Entity):
    
    
    def __init__(self, height, width, color, pos_x, pos_y, elasticity, image):
        
        super().__init__(height, width)
        
        
        self.image = pygame.transform.smoothscale(image, (width, height))
        #print(self.image.get_rect())
        self.rect = self.image.get_rect()
        
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.rect.center = (pos_x, pos_y)
        
        self.mask = pygame.mask.from_surface(self.image) #pixel-perfect collisions


        self.color = color
        #self.image.fill(self.color)
        self.elasticity = elasticity #coefficient ranging from 0 to 1
    
    
    def GetElasticity(self): return self.elasticity
    # def MoveObject(self, x, y):
    #     self.rect.move_ip(x, y)

    #@dispatch(int, int)
    #def SetCenter(self, x, y):
    #    self.rect.center = (x, y)

    #@dispatch(tuple)
    
    def GetCenter(self): return self.rect.center
    
    def SetCenter(self, position):
        self.pos_x = position[0]
        self.pos_y = position[1]
        self.rect.center = position

    def SetColor(self, color):
        self.color = color
        self.image.fill(self.color)


class MovingObject(StaticObject):
    def __init__(self, height, width, color, pos_x, pos_y, elasticity, image, mass):
       super().__init__(height, width, color, pos_x, pos_y, elasticity, image)

       self.mass = mass
       self.velocity_x = 0
       self.velocity_y = 0
       self.acceleration_x = 0
       self.acceleration_y = 0
       
       self.g_force = [0, (mass*cfg.GRAVITY)] # mg
       
    
       
    def UpdatePhysics(self, dt):
        #time between frames
        #dt = 1.0 / cfg.FPS
        
        mid_velocity_y = self.velocity_y + 0.5 * self.acceleration_y * dt
        mid_velocity_x = self.velocity_x + 0.5 * self.acceleration_x * dt
        self.pos_x += mid_velocity_x * dt * 100  # *100 because 100pixels = 1m
        self.pos_y += mid_velocity_y * dt * 100
        
        #self.pos_x += self.velocity_x * dt * 100  # *100 because 100pixels = 1m
        #self.pos_y += self.velocity_y * dt * 100
        
        self.velocity_x += self.acceleration_x * dt
        self.velocity_y += self.acceleration_y * dt
        
        self.SetCenter((self.pos_x, self.pos_y))
    
    def Move(self):
        self.UpdatePhysics(1.0 / cfg.FPS)
        
    def GetMass(self): return self.mass
        
    def GetVelocityX(self): return self.velocity_x
    def GetVelocityY(self): return self.velocity_y
    def GetAccelerationX(self): return self.acceleration_x
    def GetAccelerationY(self): return self.acceleration_y
    
    def SetVelocityX(self, velocity_x): self.velocity_x = velocity_x
    def SetVelocityY(self, velocity_y): self.velocity_y = velocity_y
    def SetAccelerationX(self, acceleration_x): self.acceleration_x = acceleration_x
    def SetAccelerationY(self, acceleration_y): self.acceleration_y = acceleration_y
    
    def GetGForce(self): return self.g_force
    
    #get all force that are acting on the object
    #resolve them
    #get vector of movement
    def ResolveForces(self, *forces):
        #print(forces)
        force = [0, 0]
        for i, j in forces:
            force[0]+=i
            force[1]+=j
        self.acceleration_x = force[0]/self.mass
        self.acceleration_y = force[1]/self.mass
        #print(self.acceleration_y)
    
    
    
    #v = eu
    #Impulse = mv - mu
    #Vb-Va = -e(Ub-Ua)
        #ignore angles for now
    def CollisionVertical(self, objCollide):
        Impulse = self.mass*(self.velocity_y*objCollide.GetElasticity() - self.velocity_y) #
        #print(self.velocity_y, end=" ")
        self.velocity_y = -self.velocity_y*objCollide.GetElasticity()
        #print(self.velocity_y)
    
    def CollisionHorizontal(self, objCollide):
        Impulse = self.mass*(self.velocity_x*objCollide.GetElasticity() - self.velocity_x) #
        #print(self.velocity_x, end=" ")
        self.velocity_x = -self.velocity_x*objCollide.GetElasticity()
        #print(self.velocity_x)
    
class Mouse():
    # def __init__(self):
    #     self.mouse_pos = pygame.mouse.get_pos()

    #pygame.mouse.get_pressed() => tuple of [lmb, mwb*, rmb]
    #[lmb, mwb*, rmb] 
    # mwb* - mousewheelbutton
    def IsLMBclicked(self):
        return pygame.mouse.get_pressed(num_buttons=3)[0]
    def IsRMBclicked(self):
        return pygame.mouse.get_pressed(num_buttons=3)[2]
    def IsMWBclicked(self):
        return pygame.mouse.get_pressed(num_buttons=3)[1]
    

    def GetMousePos(self):
        return pygame.mouse.get_pos() #x, y
    

    
    


def main():
    
    clock = pygame.time.Clock()
    run = True

    image1 = pygame.image.load("test.png").convert_alpha()
    ball_image = pygame.image.load("ball.png").convert_alpha()
    
    edgeElasticity = 1
    edgeSize = 100
    cfg.BORDER_OFFSET = edgeSize/2
    edgeLeft = StaticObject(cfg.SCREEN_HEIGHT, edgeSize, cfg.COLORS["RED"], 0, cfg.SCREEN_HEIGHT/2, edgeElasticity, image1)
    edgeTop = StaticObject(edgeSize, cfg.SCREEN_WIDTH, cfg.COLORS["RED"], cfg.SCREEN_WIDTH/2, 0, edgeElasticity, image1)
    edgeRight = StaticObject(cfg.SCREEN_HEIGHT, edgeSize , cfg.COLORS["RED"], cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT/2, edgeElasticity, image1)
    edgeBottom = StaticObject(edgeSize, cfg.SCREEN_WIDTH, cfg.COLORS["RED"], cfg.SCREEN_WIDTH/2, cfg.SCREEN_HEIGHT, edgeElasticity, image1)
    

    obj1 = StaticObject(50, 50, cfg.COLORS["RED"], 100, 100, 1, image1)
    obj2 = StaticObject(50, 50, cfg.COLORS["RED"], 100, 200, 1, image1)
    obj3 = StaticObject(50, 50, cfg.COLORS["RED"], 200, 100, 1, image1)

    mobj1 = MovingObject(100, 100, cfg.COLORS["WHITE"], 300, 100, 1, ball_image, 10)

    static_objects = pygame.sprite.Group()
    moving_objects = pygame.sprite.Group()
    
    static_objects.add(obj1)
    static_objects.add(obj2)
    static_objects.add(obj3)
    
    static_objects.add(edgeLeft)
    static_objects.add(edgeTop)
    static_objects.add(edgeRight)
    static_objects.add(edgeBottom)

    moving_objects.add(mobj1)
    
    #print(obj1.GetId(), obj2.GetId(), obj3.GetId(), mobj1.GetId())
    
    #image = pygame.transform.scale(image, (50,50))

    mouse = Mouse()

    physics_timestep = 1.0 / cfg.PHYSICS_FPS  # Фиксированный шаг физики
    accumulator = 0.0
    last_time = time.perf_counter()  # Более точное время
    
    #TIME, DISTANCE TESTING
    time1 = 0
    time2 = 0
    dist1 = 0
    dist2 = 0
    time_distance_testing = True
    
    targeted_speed_reached = False
    
    while run:

        # Расчет дельты времени
        current_time = time.perf_counter()
        dt = current_time - last_time
        last_time = current_time
        accumulator += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
       
        
        if (mouse.IsRMBclicked()):
            mobj1.SetCenter(mouse.GetMousePos())
            mobj1.SetVelocityY(0)
            mobj1.SetVelocityX(0)
            #mobj1.SetAccelerationY(0)
            
            #TIME, DISTANCE TESTING
            time1 = time.time()
            dist1 = mobj1.GetCenter()[1]
            targeted_speed_reached = False

        # FIXED TIMESTEP PHYSICS - ВАЖНО!
        # Выполняем физику фиксированными шагами
        max_physics_steps = 10  # Защита от "spiral of death"
        physics_steps = 0
        while accumulator >= physics_timestep and physics_steps < max_physics_steps:
            #if not targeted_speed_reached:
                for moving_object in moving_objects:
                    #print(moving_object.GetVelocityY())
                    
                    moving_object.ResolveForces(moving_object.GetGForce())#, [-moving_object.GetMass()*2, 0]) #gforce and some horizontal force
                    moving_object.UpdatePhysics(physics_timestep)
                    
                    obj_x, obj_y = moving_object.GetCenter()[0], moving_object.GetCenter()[1]
                    #      top
                    # left     right
                    #     bottom
                    #positions_of_edges = [left, top, right, bottom]
                    positions_of_edges = [obj_x-moving_object.GetWidth()/2, #left
                                        obj_y-moving_object.GetHeight()/2, #top
                                        obj_x+moving_object.GetWidth()/2, #right
                                        obj_y+moving_object.GetHeight()/2] #bottom
                    #print(positions_of_edges)
                    #for left, top, right, bottom in positions_of_edges:
                    moving_object_x, moving_object_y = moving_object.GetCenter()[0], moving_object.GetCenter()[1]
                    #print(moving_object_x, moving_object_y)
                    #if (moving_object.GetVelocityY() <= 0.01):
                    #    print(f"Stationary point at: {moving_object.GetCenter()}")
                    #left
                    if positions_of_edges[0] <= 0+cfg.BORDER_OFFSET:
                        #print("Collision left")
                        deltaS = 0+cfg.BORDER_OFFSET-positions_of_edges[0]
                        #print(deltaS)
                        moving_object.SetCenter((0+moving_object.GetWidth()/2+cfg.BORDER_OFFSET, moving_object_y))
                        moving_object.CollisionHorizontal(edgeLeft)
                    #top
                    if positions_of_edges[1] <= 0+cfg.BORDER_OFFSET:
                        #print("Collision top")
                        moving_object.SetCenter((moving_object_x, 0+moving_object.GetHeight()/2+cfg.BORDER_OFFSET))
                        moving_object.CollisionVertical(edgeTop)
                    #right
                    if positions_of_edges[2] >= cfg.SCREEN_WIDTH-cfg.BORDER_OFFSET:
                        #print("Collision right")
                        moving_object.SetCenter((cfg.SCREEN_WIDTH-moving_object.GetWidth()/2-cfg.BORDER_OFFSET, moving_object_y))
                        moving_object.CollisionHorizontal(edgeRight)
                    #bottom
                    if positions_of_edges[3] >= cfg.SCREEN_HEIGHT-cfg.BORDER_OFFSET:
                        #print("Collision bottom")
                        deltaS = positions_of_edges[3]-(cfg.SCREEN_HEIGHT-cfg.BORDER_OFFSET)
                        #print(deltaS)
                        moving_object.SetCenter((moving_object_x, cfg.SCREEN_HEIGHT-moving_object.GetHeight()/2-cfg.BORDER_OFFSET))
                        moving_object.CollisionVertical(edgeBottom)
                        #if moving_object.GetVelocityY() > 0.1:
                        #    moving_object.CollisionVertical(edgeBottom)
                        #else:
                        #    moving_object.SetVelocityY(0)
                                    
                    
                    #TIME, DISTANCE TESTING
                    if (time_distance_testing==True and moving_object.GetVelocityY() == 0):
                        targeted_speed_reached = True
                        #moving_object.SetAccelerationY(0)
                        
                        velocity = moving_object.GetVelocityY()
                        #moving_object.SetVelocityY(0)
                        #print(velocity)
                        time2 = time.time()
                        dist2 = mobj1.GetCenter()[1]
                        #print(time2-time1)
                        #print(dist2-dist1)
                        #time.sleep(1000)

                accumulator -= physics_timestep
                physics_steps += 1

          # Если накопилось слишком много, сбрасываем (защита от лагов)
        if accumulator > physics_timestep * 5:
            accumulator = physics_timestep * 5

        #if (pygame.sprite.spritecollide(mobj1, static_objects, False, pygame.sprite.collide_mask)):
        #    screen.fill(cfg.COLORS["BLACK"])
        #else:
        #    screen.fill(cfg.COLORS["WHITE"])

        #print(pygame.sprite.spritecollide(mobj1, static_objects, False))
        
        screen.fill(cfg.COLORS["WHITE"])

        #pygame.draw.rect(screen, colors["RED"],(SCREEN_WIDTH/2,SCREEN_HEIGHT/2,30,30))
        static_objects.draw(screen)
        moving_objects.draw(screen)

        
            
         # Отладочная информация
        font = pygame.font.Font(None, 24)
        info_text = [
            f"Graphics FPS: {cfg.FPS}",
            f"Physics FPS: {cfg.PHYSICS_FPS}", 
            #f"Target speed reached: {targeted_speed_reached}",
            f"Current y-velocity: {mobj1.GetVelocityY():.2f} m/s",
            f"Current x-velocity: {mobj1.GetVelocityX():.2f} m/s"
        ]
        
        for i, text in enumerate(info_text):
            rendered = font.render(text, True, cfg.COLORS["GREEN"])
            screen.blit(rendered, (10, 10 + i * 25))
        
        pygame.display.flip()
        clock.tick(cfg.FPS)  # Ограничиваем только графический FPS

    pygame.quit()
    
    print("Entities amount:", Entity.entity_id)
    #TIME TESTING RESULTS
    #object reached the speed of 9.81ms^-1 after 0.983212947845459s 
    #error is <2%
    #therefore it is approximately 9.81ms^-1 after 1s, that means the acceleration is working properly when divided by FPS
    
    #DISTANCE TESTING
    #WITHOUT Euler`s half step
    #when ball reached 9.81ms^-1 moving straight downwards it passed 482 pixels, therefore ~4.82m, but in reality it would have passed 4.905m
    #error is <2%
    #WITH Euler`s half step
    #mid_velocity_y = self.velocity_y + 0.5 * self.acceleration_y * dt
    #when ball reached 9.81ms^-1 moving straight downwards it passed 491 pixels, therefore ~4.91m, but in reality it would have passed 4.905m
    #error is <0.2%
    #Euler`s half step gives more precise and stable simulation
    #Its purpose is to fix using outdated speed for movement, even thought acceleration should have already changed it.
    
    #Add Fixed Timestep to prevent error increasing due to change in fps
    #Research about Velocity Verlet

    #With added timesteps
        #Physics fps and render fps are different, so the simulation does not rely on render fps
        #More physics fps, more precise simulation
        #Accumulator works along side with timesteps to perform precise rendering of physics, allows stable rendering
    
    #NEED FIXING
    #Problem with collisions
    #if the ball gets bellow the screen the collision is calculate multiple times
    #if elasticity of the edges is <1, then
    #it leads to losing all of the velocity
    
    

if __name__ == "__main__":
    main()

