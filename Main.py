import sys
from datetime import datetime

import pygame

# setting for cells
CELL_SIZE = 90

# system rgb colors
PAINT_BG = (54, 57, 62)
BORDER_BG = (30, 33, 36)
NON_COVERED_BUTTON_BG = (30, 33, 36)
COVERED_BUTTON_BG = (100, 100, 100)

# single rgb colors available for users
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SKY = (114, 137, 218)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
DARK_GREEN = (0, 51, 0)
PINK = (255, 153, 204)
YELLOW = (255, 255, 0)
ORANGE = (255, 128, 0)
CRIMSON = (102, 0, 51)
CYAN = (0, 102, 102)
LIGHT_PINK = (255, 204, 255)
PURPLE = (51, 0, 102)
BROWN = (51, 0, 0)
LIGHT_GRAY = (160, 160, 160)

# list with all available for user colors
ALL_COLORS = sorted([WHITE, SKY, RED, GREEN, BLUE, DARK_GREEN, PINK, YELLOW,
                     ORANGE, CRIMSON, CYAN, LIGHT_PINK, PURPLE, BROWN, LIGHT_GRAY, BLACK])

# images
select_img = pygame.image.load('Selected.png')


class Block:

    def __init__(self, pos: tuple[int, int]):
        self.x, self.y = pos
        self.painted = False
        self.color = None
        self.saved_outline = None

    def is_clicked(self, mouse_pos: tuple[int, int]) -> bool:
        mouse_x, mouse_y = mouse_pos
        mouse_x -= 420
        return self.x < mouse_x < self.x + CELL_SIZE and self.y < mouse_y < self.y + CELL_SIZE

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect((self.x, self.y, CELL_SIZE, CELL_SIZE))

    def draw_block(self, surface: pygame.Surface, main_color: tuple[int, int, int]):
        self.color = main_color if main_color != PAINT_BG else None
        pygame.draw.rect(surface, main_color, self.get_rect())

    def draw_outline(self, surface: pygame.Surface, outline_color: tuple[int, int, int] = None, width: int = 1):
        pygame.draw.rect(surface, outline_color if outline_color else BLACK,
                         (self.x, self.y, CELL_SIZE, CELL_SIZE), width)

    def delete_block(self, surface: pygame.Surface, outline_w: int = 1):
        self.draw_block(surface, PAINT_BG)
        self.draw_outline(surface, self.saved_outline, outline_w)
        self.color = None
        self.painted = False

    def on_click(self, surface: pygame.Surface, current_color):
        if not self.painted:
            self.painted = True
            self.draw_block(surface, current_color)
        else:
            self.delete_block(surface, 3 if self.saved_outline else 1)


class Button:

    def __init__(self, text: str, pos: tuple[int, int]):
        self.pos = pos

        self.text = text.upper()
        self.font = pygame.font.SysFont('arial', 29)

        self.size = None

    def get_btn(self, color: tuple[int, int, int] = NON_COVERED_BUTTON_BG) -> pygame.Surface:
        rendered = self.font.render(self.text, False, WHITE)
        self.size = list(rendered.get_size())
        self.size[0] += 420 - self.size[0] - self.pos[0] * 2
        btn = pygame.Surface(self.size)
        btn.fill(color)
        btn.blit(rendered, (self.size[0] // 2 - rendered.get_size()[0] // 2, 0))
        return btn

    def draw(self, surface: pygame.Surface, color: tuple[int, int, int] = NON_COVERED_BUTTON_BG):
        surface.blit(self.get_btn(color), self.pos)

    def is_covered(self, mouse_pos: list[int, int]) -> bool:
        mouse_x, mouse_y = mouse_pos
        return self.pos[0] < mouse_x < self.pos[0] + self.size[0] and self.pos[1] < mouse_y < self.pos[1] + self.size[1]


class Color:

    def __init__(self, color: tuple[int, int, int], pos: tuple[int, int]):
        self.color = color
        self.pos = pos
        self.side = 40

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, pygame.Rect((self.pos[0], self.pos[1], self.side, self.side)))

    def is_clicked(self, mouse_pos: list[int, int]) -> bool:
        mouse_x, mouse_y = mouse_pos
        mouse_y -= 280
        return self.pos[0] < mouse_x < self.pos[0] + self.side and self.pos[1] < mouse_y < self.pos[1] + self.side


class Main:

    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((1920, 1080))
        self.clock = pygame.time.Clock()

        self.left_border = pygame.Surface((420, 1080))
        self.left_border.fill(BORDER_BG)

        self.right_border = pygame.Surface((420, 1080))
        self.right_border.fill(BORDER_BG)

        self.paint = pygame.Surface((1080, 1080))
        self.paint.fill(PAINT_BG)

        self.start_painting = None
        self.end_painting = None
        self.best_time = None

        self.body = []

        self.current_color = None
        self.all_colors = []
        self.slots = []
        self.colors_surface = None

        self.buttons = [Button('exit', (15, 1020)), Button('save', (15, 15)), Button('restart', (15, 70)),
                        Button('clear', (15, 125))]

    def countdown(self, event: int):
        # TODO: create timer, which will show images "GG!", "3", "2", "1" with delay 1s
        pass

    def slots_max_limit_reached(self):
        # TODO: create and show image with error message: "Max number of colors reached"
        pass

    def clear_field(self, new: bool = True):
        if new:
            for x in range(0, self.paint.get_size()[0], CELL_SIZE):
                for y in range(0, self.paint.get_size()[1], CELL_SIZE):
                    block = Block(pos=(x, y))
                    block.draw_block(self.paint, PAINT_BG)
                    block.draw_outline(self.paint)
                    self.body.append(block)
        else:
            for block in self.body:
                block.saved_outline = None
                block.delete_block(self.paint)
            self.set_colors()
            self.best_time = None
            self.current_color = self.all_colors[0].color

    def save(self):
        if all(block.painted is False for block in self.body):
            self.clear_field(False)
        else:
            for block in self.body:
                clr = block.color
                block.saved_outline = clr
                block.delete_block(self.paint, 3 if block.color else 1)
            self.set_colors(True)
            self.start_painting = datetime.now()

    def restart(self):
        for block in self.body:
            block.delete_block(self.paint, 3 if block.saved_outline else 1)
        self.start_painting = datetime.now()

    def get_slots(self, check_colors=False) -> list:

        clrs = []

        for block in self.body:
            check = block.color if check_colors else block.saved_outline
            if check and check not in list(map(lambda c: c.color, clrs)):
                if clrs:
                    clr = Color(check, (clrs[-1].pos[0], clrs[-1].pos[1] + clrs[-1].side + 15))
                else:
                    clr = Color(check, (190, 65))
                clrs.append(clr)

        return clrs

    def set_colors(self, painting: bool = False):

        self.colors_surface = pygame.Surface((420, 565))
        self.colors_surface.fill(BORDER_BG)

        font = pygame.font.SysFont('arial', 29)
        rendered = font.render('PICK COLOR WITH MOUSE:' if not painting else 'PICK COLOR WITH KEYBOARD:', False, WHITE)
        size = list(rendered.get_size())
        size[0] += 390 - size[0]
        txt = pygame.Surface(size)
        txt.fill(NON_COVERED_BUTTON_BG)
        txt.blit(rendered, (size[0] // 2 - rendered.get_size()[0] // 2, 0))
        self.colors_surface.blit(txt, (15, 15))

        if not painting:
            self.slots = []
            x, y = 30, 65
            for color in ALL_COLORS:
                clr = Color(color, (x, y))
                self.all_colors.append(clr)
                clr.draw(self.colors_surface)
                x += clr.side + 15
                if x + 55 > self.colors_surface.get_size()[0]:
                    x = 30
                    y += clr.side + 15

            if not self.current_color:
                self.current_color = self.all_colors[0].color

        else:
            self.slots = self.get_slots()
            for clr in self.slots:
                clr.draw(self.colors_surface)
                rendered = font.render(str(self.slots.index(clr) + 1), False, WHITE)
                txt = pygame.Surface(rendered.get_size())
                x, y = clr.pos
                txt.fill(BORDER_BG)
                txt.blit(rendered, (0, 0))
                self.colors_surface.blit(txt, (x - 25, y + 5))

            if self.slots:
                self.current_color = self.slots[0].color
                self.all_colors = []

    def check_painted(self):
        with_outline = list(filter(lambda x: x.saved_outline, self.body))
        painted = list(filter(lambda x: x.painted, self.body))
        if with_outline and len(with_outline) == len(painted) and all(block.painted for block in with_outline):
            self.end_painting = datetime.now()
            build_in = self.datetime_to_str(self.start_painting, self.end_painting)
            build_in = build_in.ljust(build_in.index('.') + 3, '0')
            if self.best_time is None or float(build_in) < float(self.best_time):
                self.best_time = build_in
                self.render(f'Best time: {build_in}', (15, 125))
            self.render(f'Last time: {build_in}', (15, 70))
            cur = self.current_color
            self.save()
            self.current_color = cur

    def set_selected(self, painted: bool = True):
        par = self.slots if painted else self.all_colors
        cur_color_ind = list(map(lambda k: k.color, par)).index(self.current_color)
        for i in par:
            x, y = i.pos
            if cur_color_ind == par.index(i):
                self.colors_surface.blit(select_img, (x + 7, y + 7))
            else:
                pygame.draw.rect(self.colors_surface, i.color, pygame.Rect(x + 7, y + 7, 25, 25))

    def render(self, text: str, pos: tuple[int, int]):

        font = pygame.font.SysFont('arial', 29)
        rendered = font.render(text, False, WHITE)
        size = list(rendered.get_size())
        size[0] += 390 - size[0]
        txt = pygame.Surface(size)
        txt.fill(NON_COVERED_BUTTON_BG)
        txt.blit(rendered, (size[0] // 2 - rendered.get_size()[0] // 2, 0))

        self.right_border.blit(txt, pos)

    @staticmethod
    def datetime_to_str(start: datetime, end: datetime) -> str:

        t = str((end - start).total_seconds())
        sec, msec = t.split('.')
        msec = msec[:2]

        return f'{sec}.{msec}'

    def event_loop(self):
        for event in pygame.event.get():

            mouse_pos = list(pygame.mouse.get_pos())

            for button in self.buttons:
                if button.size and button.is_covered(mouse_pos):
                    button.draw(self.left_border, COVERED_BUTTON_BG)
                else:
                    button.draw(self.left_border)

            if event.type == pygame.KEYDOWN and not self.all_colors:
                keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4,
                        pygame.K_6: 5, pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8}
                if event.key in keys:
                    ind = keys[event.key]
                    if ind < len(self.slots):
                        self.current_color = self.slots[ind].color

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    border_width, _ = self.left_border.get_size()
                    left_line = self.screen.get_size()[0] - border_width - self.paint.get_size()[0]
                    right_line = self.screen.get_size()[0] - border_width
                    if left_line < mouse_pos[0] < right_line:
                        for block in self.body:
                            if block.is_clicked(mouse_pos):
                                if not block.painted and block.saved_outline \
                                        and self.current_color != block.saved_outline:
                                    continue
                                block.on_click(self.paint, self.current_color)
                                self.check_painted()
                    elif 0 <= mouse_pos[0] <= left_line:
                        for color in self.all_colors:
                            if color.is_clicked(mouse_pos):
                                colors = self.get_slots(True)
                                if len(colors) == 9 and color.color not in list(map(lambda x: x.color, colors)):
                                    self.slots_max_limit_reached()
                                else:
                                    self.current_color = color.color
                        for button in self.buttons:
                            if button.is_covered(mouse_pos):
                                if button.text == 'EXIT':
                                    pygame.quit()
                                    sys.exit()
                                if button.text == 'SAVE':
                                    self.save()
                                if button.text == 'CLEAR':
                                    self.clear_field(False)
                                if button.text == 'RESTART':
                                    self.restart()

    def run(self):

        self.clear_field()
        self.set_colors()

        while True:
            self.event_loop()

            self.screen.blit(self.paint, (420, 0))
            self.screen.blit(self.left_border, (0, 0))
            self.screen.blit(self.right_border, (1500, 0))
            pygame.draw.line(self.screen, BLACK, (420, 0), (420, 1080), 4)
            pygame.draw.line(self.screen, BLACK, (1500, 0), (1500, 1080), 4)

            if not self.all_colors:
                self.set_selected()
                self.render(f'Current time: {self.datetime_to_str(self.start_painting, datetime.now())}', (15, 15))
            else:
                self.set_selected(False)
                pygame.draw.rect(self.right_border, BORDER_BG, pygame.Rect(0, 0, 420, 300))
            self.left_border.blit(self.colors_surface, (0, 280))

            pygame.display.update()
            self.clock.tick(60)  # fps


if __name__ == '__main__':
    Main().run()
