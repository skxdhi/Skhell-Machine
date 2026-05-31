import pygame

class Button:
    def __init__(self, pos, size, dir, image, func, visual=None, name="", type=None):
        self.pos = pos
        self.size = size
        self.w = size[0]
        self.h = size[1]
        self.dir = dir
        self.image = image
        self.func = func
        self.visual = visual
        self.name = name
        self.type = type

    def hovering(self):
        rect = pygame.Rect(self.pos[0], self.pos[1], self.w, self.h)
        return rect.collidepoint(pygame.mouse.get_pos())

    def click(self):
        self.func()

    def draw(self):
        screen = pygame.display.get_surface()

        if self.visual is not None:
            self.visual(self)

        transformed = pygame.transform.scale(
            self.image,
            (int(self.w), int(self.h))
        )

        rotated = pygame.transform.rotate(transformed, self.dir * -90)

        base_rect = transformed.get_rect(topleft=(self.pos[0], self.pos[1]))
        rotated_rect = rotated.get_rect(center=base_rect.center)

        rotated.set_alpha(200 if self.hovering() else 128)

        screen.blit(rotated, rotated_rect)