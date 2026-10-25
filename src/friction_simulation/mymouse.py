import pygame

class Mouse:

    def __init__(self):
        self.draggable_object    = None

    # -- Button state --

    def is_lmb_clicked(self):
        return pygame.mouse.get_pressed(num_buttons=3)[0]

    def is_rmb_clicked(self):
        return pygame.mouse.get_pressed(num_buttons=3)[2]

    def is_mwb_clicked(self):
        return pygame.mouse.get_pressed(num_buttons=3)[1]

    # -- Position --

    def get_mouse_pos(self):
        return pygame.mouse.get_pos()