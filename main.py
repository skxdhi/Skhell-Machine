import math

import pygame
import sys
import os
import random
import anim
import buttons
import cells as cells_module
import json
import base64

import sympy as sp

eps = sp.Symbol('eps', positive=True, infinitesimal=True)
omega = 1 / eps


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
icon = pygame.image.load(resource_path('icon.png')).convert_alpha()
pygame.display.set_icon(icon)
pygame.display.set_caption('Skhell Machine')
font = pygame.font.Font(resource_path('nokiafcellua.ttf'), 24)
clock = pygame.time.Clock()
image_size = 32
x = True
lerp = 0
ticks = 0
next_id = 0
running = False
zoom = 1.0
eatencells = {}
effects = {}
undocells = {}
edit_button = False
editing = False
selectidx = 0
dt = 0
selected = {
    'direction': 0,
    'cell_name': 'mover'
}

selected_adjustable_key = None
dropdown_open = False
selected_category = None
selected_subcategory = None
menu_open = False
music_muted = False
swap_knights = False

typing_number, typing_number_with_dot = False, False
number_text = ""

initstate = True
initcells = {}

updated = set()

grid_dimensions = (50, 50)

camera_pos = {
    'x': 0,
    'y': 0,
}

def format_cell_name(name):
    words = name.split()

    new_words = []
    for w in words:
        if w.lower() == "cw":
            new_words.append("CW")
        elif w.lower() == "ccw":
            new_words.append("CCW")
        else:
            new_words.append(w.capitalize())

    return " ".join(new_words)


celltypes = {
    'mover': {'desc': 'Moves forward one space every tick'},
    #'diagonal mover': {'desc': 'Moves forward one space diagonally every tick'},
    'wall': {'desc': 'Stops cells that attempt to move it'},
    'push': {'desc': 'Can be moved by anything'},
    'slide': {'desc': 'Can only be pushed on the indicated sides'},
    '3-way push': {'desc': 'Can only be pushed on the indicated sides'},
    '1-way push': {'desc': 'Can only be pushed on the indicated side'},
    'bent slide': {'desc': 'Can only be pushed on the indicated sides'},
    'cw rotator': {'desc': 'Rotates adjacent cells 90 degrees clockwise'},
    'ccw rotator': {'desc': 'Rotates adjacent cells 90 degrees counterclockwise'},
    '180 rotator': {'desc': 'Rotates adjacent cells 180 degrees'},
    'random rotator': {'desc': 'Rotates adjacent cells 90 degrees clockwise or counterclockwise'},
    'trash': {'desc': 'Deletes cells that move into it'},
    'enemy': {'desc': 'Deletes cells that move into it and then it deletes itself'},
    'generator': {'desc': 'Clones the cell behind it and puts the clone in front of it'},
    'disabler': {'desc': 'Prevents adjacent cells from updating'},
    'weight': {'desc': 'Subtracts 1 unit of bias when pushed'},
    'anti weight': {'desc': 'Adds 1 unit of bias when pushed'},
    'nano weight': {'desc': 'Cannot be moved by itself, e.g. A repulsor making a cell move'},
    'anti nano weight': {'desc': 'Can only be moved by itself, e.g. A repulsor making a cell move'},
    'repulsor': {'desc': 'Pushes adjacent cells away from it'},
    'enabler': {'desc': 'Prevents adjacent cells from being disabled'},
    'gold': {'desc': 'Can only be moved orthogonally (not diagonally)'},
    'lead': {'desc': 'Can only be moved diagonally'},
    'random push': {'desc': 'Like the Push cell but it has a 1 in 2 chance to not be pushable'},
    'puller': {'desc': 'Like the Mover cell except it moves the cells behind it rather than infront, also it cant move if there is something infront of it'},
    'impulsor': {'desc': 'The opposite of a Repulsor, pulls cells towards it rather than pushing them away'},
    #'diagonal puller': {'desc': 'A Puller that moves forward 1 space diagonally every tick'},
    'cw gear': {'desc': 'Makes surrounding cells orbit around it in a clockwise motion 2x faster'},
    'ccw gear': {'desc': 'Makes surrounding cells orbit around it in a counterclockwise motion 2x faster'},
    '180 gear': {'desc': 'Makes surrounding cells orbit around it 4x faster'},
    'random gear': {'desc': 'Makes surrounding cells orbit around it either clockwise or counterclockwise'},
    'jam': {'desc': 'When a Gear tries to move it, it will stop the entire gear'},
    'mirror': {'desc': 'Swaps the two cells that the arrows are pointing at'},
    'a weight': {'desc': "Adds 'A' units of bias when pushed, I'm sure that will end well"},
    'leaper': {'desc': 'A Mover that has a run of 2, meaning it will jump over the cell infront of it'},
    'leap puller': {'desc': 'A Puller that has a run of 2, meaning it will jump over the cell infront of it'},
    'ccw knight': {'desc': 'A Mover with a run of 2 and a rise of 1'},
    'cw knight': {'desc': 'A Mover with a run of 2 and a rise of -1'},
    'conductance': {'desc': 'Can only be moved if the bias is not 1'},
    'friend': {'desc': 'Enemy but friendly, if you kill him im gonna cry'},
    'advancer': {'desc': 'A Puller that can move cells infront of it'},
    'straight diverger': {'desc': 'When a cell tries to move on one end it will be transported to the other end'},
    'curve diverger': {'desc': 'A Straight Diverger but an end is bent 90 degrees'},
    'cw generator': {'desc': 'A Generator but the output direction is bent 90 degrees clockwise, and the outputted cell is rotated too'},
    'ccw generator': {'desc': 'A Generator but the output direction is bent 90 degrees counterclockwise, and the outputted cell is rotated too'},
    'bi generator': {'desc': 'A CW Generator combined with a CCW Generator, that means it has 2 outputs'},
    'tri generator': {'desc': "A Bi Generator combined with a normal Generator, that means it has 3 outputs.. I'm already tired of this"},
    'cw valve generator': {'desc': 'A CW Generator combined with a normal Generator, that means it has 2 outputs'},
    'ccw valve generator': {'desc': 'A CCW Generator combined with a normal Generator, that means it has 2 outputs'},
    #'diagonal generator': {'desc': 'A Generator but its input and output are diagonal like a Diagonal Mover'},
    'cw skew generator': {'desc': 'A Generator but its output is bent 45 degrees clockwise'},
    'ccw skew generator': {'desc': 'A Generator but its output is bent 45 degrees counterclockwise'},
    'bi skew generator': {'desc': 'A CW Skew Generator combined with a CCW Skew Generator, that means it has 2 outputs'},
    'tri skew generator': {'desc': 'A Bi Skew Generator combined with a normal Generator, that means it has 3 outputs... OH NOT THIS AGAI-'},
    'ungeneratable': {'desc': 'When a Generator tries to generate this cell, nothing happens, but the Generator still pushes the cell infront of it as if it did something'},
    'adjustable weight': {'desc': 'A Weight but you can change how much force it takes away, negative numbers means it adds force'},
    'infinite weight': {'desc': 'A Weight that takes away an infinite amount of bias when pushed'},
    'anti infinite weight': {'desc': 'A Weight that adds an infinite amount of bias when pushed'},
    'super mover': {'desc': 'A Mover that moves infinitely fast, with infinite force'},
    'restrictor': {'desc': 'Limits the force pushing it to 1 unit of force'},
    'compensator': {'desc': 'Sets the force pushing it to 1 if the amount of force is less than 1'},
    'super puller': {'desc': 'A Puller that moves infinitely fast, with infinite force'},
    'adjustable mover': {'desc': 'A Mover in which you can change its properties'},
    #'cw veerer': {'desc': 'A Mover but when it hits a wall it turns 90 degrees clockwise'},
    #'ccw veerer': {'desc': 'A Mover but when it hits a wall it turns 90 degrees counterclockwise'},
    'number': {'desc': 'Stores a number, can be used to do math'},
    'straight wire': {'desc': 'A Wire, it can be used to connect an output to an input and vice versa'},
    'curve wire': {'desc': 'A Wire, it can be used to connect an output to an input and vice versa'},
    'add': {'desc': 'Outputs the sum of the 2 inputs'},
    'monogeneratable': {'desc': 'When a Generator tries to generate it, it will output Ungeneratable cells instead'},
    'semigeneratable': {'desc': 'Has a 1/2 chance to act like Ungeneratable'},
    'adjustable generatable': {'desc': 'When a Generator tries to generate it, it will output a copy of itself but with a count decreased by 1, if the counter is 0 it will act like Ungeneratable'},
    'antigeneratable': {'desc': 'When a Generator tries to generate it, nothing happens; think of it as disabling the generator'},
    'strong enemy': {'desc': 'An Enemy but it has two lives'},
    'adjustable enemy': {'desc': 'When a cell collides with it, its counter will decrease by 1, if the counter is 1 it will act like an Enemy'},
    'weak enemy': {'desc': 'An Enemy but it doesnt destroy the cell that collided with it, basically a reversed Trash'},
    'physical generator': {'desc': 'Like a normal Generator, but when its being blocked by something it moves itself backwards to create space'},
    'cw half rotator': {'desc': 'Rotates adjacent cells 45 degrees clockwise'},
    'ccw half rotator': {'desc': 'Rotates adjacent cells 45 degrees counterclockwise'},
    #'cw half veerer': {'desc': 'A Mover but when it hits a wall it turns 45 degrees clockwise'},
    #'ccw half veerer': {'desc': 'A Mover but when it hits a wall it turns 45 degrees counterclockwise'},
    'cw half gear': {'desc': 'Makes surrounding cells orbit around it in a clockwise motion'},
    'ccw half gear': {'desc': 'Makes surrounding cells orbit around it in a counterclockwise motion'},
    'random half gear': {'desc': 'Makes surrounding cells orbit around either clockwise or counterclockwise'},
    'random half rotator': {'desc': 'Rotates adjacent cells 45 degrees clockwise or counterclockwise'},
    'cw fast rotator': {'desc': 'Rotates adjacent cells 135 degrees clockwise'},
    'ccw fast rotator': {'desc': 'Rotates adjacent cells 135 degrees counterclockwise'},
    'cw fast gear': {'desc': 'Makes surrounding cells orbit around it in a clockwise motion 3x faster'},
    'ccw fast gear': {'desc': 'Makes surrounding cells orbit around it in a counterclockwise motion 3x faster'},
    'random fast rotator': {'desc': 'Rotates adjacent cells 135 degrees clockwise or counterclockwise'},
    'random fast gear': {'desc': 'Makes surrounding cells orbit around it either clockwise or counterclockwise 3x faster'},
    'veerer': {'desc': 'A Mover but when it cannot move it rotates a certain amount, that amount is adjustable with multiples of 0.5, 0.5 means 45 degree rotation, it can also be negative, there is another switch for random rotation'},
    'infinitesimal weight': {'desc': 'A Weight that takes away an infinitesimal amount of bias when pushed, an infinitesimal is a number that is bigger than 0 but less that every positive real number'},
    'anti infinitesimal weight': {'desc': 'A Weight that adds an infinitesimal amount of bias when pushed, an infinitesimal is a number that is bigger than 0 but less that every positive real number'},
}

def make_save_code():
    global running
    running = False
    data = []

    for i, cell in cells.items():
        if is_border(i):
            continue

        data.append({
            "x": cell.x,
            "y": cell.y,
            "direction": cell.direction,
            "name": cell.name,
            "properties": cell.properties
        })

    raw = json.dumps(data)
    code = base64.b64encode(raw.encode()).decode()
    return code

def load_save_code(code):
    global cells, effects, eatencells, next_id, running
    running = False

    raw = base64.b64decode(code.encode()).decode()
    data = json.loads(raw)

    cells = {}
    effects = {}
    eatencells = {}
    next_id = 0

    grid_borders(grid_dimensions[0], grid_dimensions[1])
    border_ids.clear()
    border_ids.update(cells.keys())

    for item in data:
        add_cell(
            item["name"],
            item["x"],
            item["y"],
            item["direction"],
            properties=item.get("properties", {})
        )

    set_init_state()

class Vec2:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def multiply(self, magnitude):
        return Vec2(self.x*magnitude,self.y*magnitude)

    def negate(self):
        return Vec2(-self.x,-self.y)

    def rotate(self, degrees):
        degrees = degrees*90
        x = self.x * math.cos(math.radians(-degrees)) + self.y * math.sin(math.radians(-degrees))
        y = -self.x * math.sin(math.radians(-degrees)) + self.y * math.cos(math.radians(-degrees))
        return Vec2(round(x), round(y))

celltypes = {
    format_cell_name(name): data
    for name, data in celltypes.items()
}

def load_all_images(directory):
    images = {}

    for filename in os.listdir(directory):
        if filename.endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(directory, filename)

            raw_name = os.path.splitext(filename)[0]
            formatted_name = format_cell_name(raw_name)

            images[raw_name] = pygame.image.load(path).convert_alpha()
            images[formatted_name] = images[raw_name]

    return images

def load_all_audio(directory):
    audio = {}

    for filename in os.listdir(directory):
        if filename.endswith((".mp3", ".wav", ".ogg")):
            path = os.path.join(directory, filename)

            raw_name = os.path.splitext(filename)[0]

            audio[raw_name] = pygame.mixer.Sound(path)

    return audio


def add_tag(tag_name, pairs):
    for pair in pairs:
        cell_name = format_cell_name(pair[0])
        celltypes[cell_name][tag_name] = pair[1]


def get_tag(cell_name, key, *args):
    cell_name = format_cell_name(cell_name)

    if cell_name in celltypes:
        value = celltypes[cell_name].get(key, None)

        if callable(value):
            return value(*args)

        return value

    return None


def get_tag_raw(cell_name, key):
    cell_name = format_cell_name(cell_name)

    if cell_name in celltypes:
        return celltypes[cell_name].get(key, None)

    return None


def adjustable(cell_names, inputs, draw_func=None):
    for cell_name in cell_names:
        add_tag('adjustable', [(cell_name, inputs)])
        add_tag('draw_properties', [(cell_name, draw_func)])


def get_adjustable(cell_name):
    return get_tag(cell_name, 'adjustable')


def get_current_adjustable_data():
    return get_adjustable(selected['cell_name'].lower())


def mouse_in_rect_obj(rect):
    return rect.collidepoint(pygame.mouse.get_pos())


def is_unbreakable(cell_name, force_name, side):
    return get_tag(cell_name, 'unbreakable', force_name, side)


def get_selected_properties():
    data = get_current_adjustable_data()

    if data is None:
        return {}

    return {
        key: value[0]
        for key, value in data.items()
    }


def draw_ghost_properties(cell_name, x, y, direction):
    draw_func = get_tag_raw(cell_name, 'draw_properties')

    if draw_func is None:
        return

    fake_cell = cells_module.Cell(x, y, direction, cell_name)

    draw_func(fake_cell, get_selected_properties(), alpha=128)


def trash_unbreakable(force_name, side):
    return force_name != 'rotate'

def weak_collide(cell_id, other_cell_id):
    x = cells[cell_id].x
    y = cells[cell_id].y

    cell_delete(cell_id, x, y)

    return True

def normal_collide(cell_id, other_cell_id):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)
    cell_delete(cell_id, x, y)

    return True

def strong_collide(cell_id, other_cell_id):
    x = cells[cell_id].x
    y = cells[cell_id].y

    cell_delete(other_cell_id, x, y)
    cells[cell_id].name = 'enemy'

    return True

def adjustable_enemy_collide(cell_id, other_cell_id):
    x = cells[cell_id].x
    y = cells[cell_id].y

    cell_delete(other_cell_id, x, y)
    cells[cell_id].properties['Count'] -= 1

    if cells[cell_id].properties['Count'] <= 0:
        cell_delete(cell_id, x, y)

    return True

def trash_collide(cell_id, other_cell_id):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)

    return True

add_tag('unbreakable', {('wall', True),('trash', trash_unbreakable)})
add_tag('can_collide', {('enemy', normal_collide),('trash', trash_collide),('friend', normal_collide),('strong enemy', strong_collide),('adjustable enemy', adjustable_enemy_collide),('weak enemy', weak_collide)})
add_tag('is_friendly', {('friend', True)})
add_tag('is_unfriendly', {('enemy', True)})
add_tag('gen_rotate', [
    ('cw generator', [1]),
    ('ccw generator', [-1]),
    ('bi generator', [1, -1]),
    ('tri generator', [1, -1, 0]),
    ('cw valve generator', [1, 0]),
    ('ccw valve generator', [-1, 0]),
    ('cw skew generator', [0.5]),
    ('ccw skew generator', [-0.5]),
    ('bi skew generator', [0.5, -0.5]),
    ('tri skew generator', [0.5, -0.5, 0]),
])

add_tag('gen_move', [
    #('diagonal generator', -0.5)
])

add_tag('physical', [
    ('physical generator', 'physical')
])

add_tag('wiring', [
    ('straight wire', [0,2]),
    ('curve wire', [0,3]),
])

def adjustable_generatable(cell, side):
    count = cell.properties.get('Count', 0)

    if count <= 0:
        return 0

    new_props = cell.properties.copy()
    new_props['Count'] = count - 1

    return {
        'name': cell.name,
        'properties': new_props
    }

def semigeneratable(cell, side):
    return 0 if random.random() < 0.5 else 'semigeneratable'

add_tag('gen_as', [
    ('ungeneratable', 0),
    ('monogeneratable', 'ungeneratable'),
    ('semigeneratable', semigeneratable),
    ('adjustable generatable', adjustable_generatable),
    ('antigeneratable', 'BLOCK_GENERATOR'),
])

def get_wiring(cell_name):
    return get_tag(cell_name, 'wiring')

def is_side_wire(cell_name, side):
    return side in get_wiring(cell_name)

def genzero(cell_name):
    return get_tag(cell_name, 'gen_as') == 0


images = load_all_images(resource_path('textures'))
audio = load_all_audio(resource_path('audio'))

music = audio['Load 15 cells']
music.play(loops=-1)

border_ids = {}
cells = {}

edit_icon = images['edit'] or images['notex']

subcategories = {
    'movers': ['mover', 'leaper', 'cw knight', 'ccw knight', 'super mover', 'adjustable mover', 'advancer', 'veerer'],
    'pullers': ['puller', 'leap puller', 'super puller', 'advancer'],
    'walls': ['wall'],
    'pushables': ['push', 'slide', '3-way push', '1-way push', 'bent slide', 'random push'],
    'weights': ['weight', 'anti weight', 'nano weight', 'anti nano weight', 'adjustable weight', 'infinite weight', 'infinitesimal weight', 'anti infinite weight', 'anti infinitesimal weight', 'a weight', 'gold', 'lead', 'conductance', 'restrictor', 'compensator'],
    'rotators': ['cw rotator', 'cw half rotator', 'cw fast rotator', 'ccw rotator', 'ccw half rotator', 'ccw fast rotator', 'random rotator', 'random half rotator', 'random fast rotator', '180 rotator'],
    'trashes': ['trash'],
    'enemies': ['enemy','strong enemy','adjustable enemy','weak enemy','friend'],
    'generation': ['ungeneratable', 'monogeneratable', 'semigeneratable', 'adjustable generatable', 'antigeneratable'],
    'generators': ['generator','cw generator','cw valve generator','ccw generator','ccw valve generator','bi generator','tri generator','cw skew generator','ccw skew generator','bi skew generator','tri skew generator','physical generator'],
    'effect givers': ['disabler', 'enabler'],
    'repulsors': ['repulsor'],
    'impulsors': ['impulsor'],
    'gears': ['cw gear', 'ccw gear', '180 gear', 'random gear', 'cw half gear', 'ccw half gear', 'random half gear', 'cw fast gear', 'ccw fast gear', 'random fast gear', 'jam'],
    'mirrors': ['mirror'],
    'divergers': ['straight diverger','curve diverger'],
    'numbers': ['number'],
    'wires': ['straight wire', 'curve wire'],
    'operations': ['add'],
}

categories = [
    {
        'name': 'Base',
        'texture': images['push'] or images['notex'],
        'sub': [subcategories['pushables'], subcategories['walls'], subcategories['weights']],
    },
    {
        'name': 'Movers',
        'texture': images['mover'] or images['notex'],
        'sub': [subcategories['movers'], subcategories['pullers']],
    },
    {
        'name': 'Rotators',
        'texture': images['cw rotator'] or images['notex'],  # fix texture name
        'sub': [subcategories['rotators'], subcategories['gears']],
    },
    {
        'name': 'Destroyers',
        'texture': images['trash'] or images['notex'],
        'sub': [subcategories['trashes'], subcategories['enemies']],
    },
    {
        'name': 'Forcers',
        'texture': images['repulsor'] or images['notex'],
        'sub': [subcategories['repulsors'], subcategories['impulsors'], subcategories['gears'], subcategories['mirrors']],
    },
    {
        'name': 'Recreation',
        'texture': images['generator'] or images['notex'],
        'sub': [subcategories['generators'], subcategories['generation']],
    },
    {
        'name': 'Divergers',
        'texture': images['straight diverger'] or images['notex'],
        'sub': [subcategories['divergers']],
    },
    {
        'name': 'Math',
        'texture': images['number'] or images['notex'],
        'sub': [subcategories['numbers'], subcategories['wires'], subcategories['operations']],
    },
    {
        'name': 'Miscellaneous',
        'texture': images['disabler'] or images['notex'],
        'sub': [subcategories['effect givers']],
    },
]


def draw_sides(cell, properties, alpha=255):
    x, y, direction = cell.x, cell.y, cell.direction

    sides = ['Right', 'Down', 'Left', 'Up']

    for i, side in enumerate(sides):
        value = properties.get(side, 'None')

        if value == 'None':
            continue

        name = value.lower() + 'side'

        size = int(image_size * zoom)

        screen_x = x * image_size * zoom + camera_pos['x']
        screen_y = y * image_size * zoom + camera_pos['y']

        base_rect = pygame.Rect(screen_x, screen_y, size, size)

        img = pygame.transform.scale(images[name] or images['notex'], (size, size))
        rotated = pygame.transform.rotate(img, (direction + i) * -90)
        rotated.set_alpha(alpha)

        rotated_rect = rotated.get_rect(center=base_rect.center)
        screen.blit(rotated, rotated_rect)

def draw_none(cell, properties, alpha=255):
    pass

def draw_number(cell, properties, alpha=255):
    x, y = cell.x, cell.y

    value = list(properties.values())[0]

    outlinecolor = pygame.color.Color(189, 222, 255) if cell.name == 'number' else images[cell.name].get_at((1, 7))

    text = font.render(str(value), True, (255, 255, 255))
    text = pygame.transform.scale(text, (text.get_width()*zoom/2, text.get_height()*zoom/2))
    text.set_alpha(alpha)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    cell_size = image_size * zoom

    text_rect = text.get_rect(
        center=(
            screen_x + cell_size / 2,
            screen_y + cell_size / 2
        )
    )

    for dx, dy in [(-zoom, -zoom), (-zoom, 0), (-zoom, zoom), (0, -zoom), (0, zoom), (zoom, -zoom), (zoom, 0), (zoom, zoom)]:
        textt = font.render(str(value), True, outlinecolor)
        textt = pygame.transform.scale(textt, (textt.get_width() * zoom / 2, textt.get_height() * zoom / 2))
        textt.set_alpha(alpha)
        textt_rect = textt.get_rect(
            center=(
                dx + screen_x + cell_size / 2,
                dy + screen_y + cell_size / 2
            )
        )
        screen.blit(textt, textt_rect)

    screen.blit(text, text_rect)

def draw_fraction(cell, properties, alpha=255):
    x, y = cell.x, cell.y

    value = str(list(properties.values())[0]) + '/' + str(list(properties.values())[1])

    outlinecolor = images[cell.name].get_at((1, 7))

    text = font.render(str(value), True, (255, 255, 255))
    text = pygame.transform.scale(text, (text.get_width()*zoom/2, text.get_height()*zoom/2))
    text.set_alpha(alpha)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    cell_size = image_size * zoom

    text_rect = text.get_rect(
        center=(
            screen_x + cell_size / 2,
            screen_y + cell_size / 2
        )
    )

    for dx, dy in [(-zoom, -zoom), (-zoom, 0), (-zoom, zoom), (0, -zoom), (0, zoom), (zoom, -zoom), (zoom, 0), (zoom, zoom)]:
        textt = font.render(str(value), True, outlinecolor)
        textt = pygame.transform.scale(textt, (textt.get_width() * zoom / 2, textt.get_height() * zoom / 2))
        textt.set_alpha(alpha)
        textt_rect = textt.get_rect(
            center=(
                dx + screen_x + cell_size / 2,
                dy + screen_y + cell_size / 2
            )
        )
        screen.blit(textt, textt_rect)

    screen.blit(text, text_rect)


adjustable(
    subcategories['rotators'],
    {
        'Right': ['None', ['None', 'Push', 'Wall']],
        'Down': ['None', ['None', 'Push', 'Wall']],
        'Left': ['None', ['None', 'Push', 'Wall']],
        'Up': ['None', ['None', 'Push', 'Wall']]
    },
    draw_sides
)

adjustable(
    ['adjustable weight'],
    {
        'Weight': [0, 'number'],
    },
    draw_number
)

adjustable(
    ['adjustable mover'],
    {
        'Speed': [1, 'number'],
        'Delay': [1, 'number'],
        'Bias': [1, 'number'],
        'Rise': [0, 'number'],
        'Run': [1, 'number'],
    },
    draw_fraction
)

adjustable(
    ['number'],
    {
        'Value': [0, 'number'],
    },
    draw_number
)

adjustable(
    ['adjustable generatable', 'adjustable enemy'],
    {
        'Count': [0, 'number'],
    },
    draw_number
)

adjustable(
    ['veerer'],
    {
        'Rotation': [0, 'number+dot'],
        'Random': [False, 'bool'],
    },
    draw_number
)

def same_axis(dir1, dir2):
    return dir1 % 2 == dir2 % 2

def is_border(id):
    return id in border_ids


def out_of_bounds(x, y):
    return x < 0 or y < 0 or x > grid_dimensions[0] or y > grid_dimensions[1]


def is_on_screen(x, y):
    size = image_size * zoom

    screen_x = x * size + camera_pos['x']
    screen_y = y * size + camera_pos['y']

    if screen_x + size < 0: return False
    if screen_y + size < 0: return False
    if screen_x > screen.get_width(): return False
    if screen_y > screen.get_height(): return False

    return True


def mouse_in_rect(rect):
    mouse_pos = pygame.mouse.get_pos()
    return rect.collidepoint(mouse_pos)


def get_cell_idx_at_pos(x, y):
    for i in cells:
        if cells[i].x == x and cells[i].y == y:
            return i
    return None


def add_cell(cell_name, x, y, direction, oldx=None, oldy=None, olddirection=None, effectlist=None, properties=None):
    if get_cell_idx_at_pos(x, y) is not None:
        return

    global next_id
    next_id += 1

    cell = cells_module.Cell(
        x=x,
        y=y,
        direction=direction,
        name=cell_name,
        oldx=oldx,
        oldy=oldy,
        olddirection=olddirection,
        effects=effectlist,
        properties=properties,
    )

    cells[next_id] = cell
    effects[next_id] = cell.effects


def delete_cell(x, y):
    idx = get_cell_idx_at_pos(x, y)
    if idx is not None and not is_border(idx):
        cells.pop(idx)


def fill(pos1, pos2, cell_name):
    x1, y1 = pos1
    x2, y2 = pos2
    structure = {}

    min_x, max_x = sorted((x1, x2))
    min_y, max_y = sorted((y1, y2))

    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            delete_cell(x, y)
            if cell_name is not None:
                add_cell(cell_name, x, y, selected['direction'])

def visual_cell_name(cell_name):
    if swap_knights:
        if cell_name == 'cw knight':
            return 'ccw knight'
        if cell_name == 'ccw knight':
            return 'cw knight'

    return cell_name


def grid_borders(w, h):
    fill((0, 0), (w, h), 'wall')
    fill((1, 1), (w - 1, h - 1), None)


# Setup
grid_borders(grid_dimensions[0], grid_dimensions[1])
border_ids = set(cells.keys())


# ------

def draw_cell(cell_name, x, y, direction):
    if not is_on_screen(x, y):
        return

    size = int(image_size * zoom)

    draw_name = visual_cell_name(cell_name)

    image = pygame.transform.scale(
        images[draw_name] or images['notex'],
        (size, size)
    )

    rotated_image = pygame.transform.rotate(image, direction * -90)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    rect = image.get_rect(topleft=(screen_x, screen_y))
    rotated_rect = rotated_image.get_rect(center=rect.center)

    screen.blit(rotated_image, rotated_rect)


def draw_eaten_cell(cell_name, x, y, direction):
    if not is_on_screen(x, y):
        return

    size = int(image_size * zoom)

    shrink = lerp * size


    draw_name = visual_cell_name(cell_name)

    image = pygame.transform.scale(
        images[draw_name] or images['notex'],
        (size-shrink, size-shrink)
    )

    rotated_image = pygame.transform.rotate(image, direction * -90)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    rect = image.get_rect(center=(
        screen_x + size / 2,
        screen_y + size / 2
    ))
    rotated_rect = rotated_image.get_rect(center=rect.center)

    screen.blit(rotated_image, rotated_rect)


def draw_bg():
    for x in range(1, grid_dimensions[0]):
        for y in range(1, grid_dimensions[1]):
            draw_cell('bg', x, y, 0)


button_list = []

def add_button(texture, size, position, direction, onclick, name, update_visual=None):
    button_list.append(
        buttons.Button(
            position,
            size,
            direction,
            texture,
            onclick,
            update_visual,
            name
        )
    )


def play_button_visual(button):
    if running:
        button.image = images['slide'] or images['notex']
        button.dir = 1
    else:
        button.image = images['mover'] or images['notex']
        button.dir = 0

def toggle_mute():
    global music_muted

    music_muted = not music_muted

    if music_muted:
        pygame.mixer.pause()
    else:
        pygame.mixer.unpause()

def toggle_knights():
    global swap_knights
    swap_knights = not swap_knights


def cell_button_visual(button):
    if selected_category is None or selected_subcategory is None:
        return

    cat_index = selected_category
    sub_index = selected_subcategory
    cell_index = button.cell_index

    cat_x = cat_index * 70 + 10
    base_y = screen.get_height() - 70

    sub_y = base_y - 50 * (sub_index + 1)

    button_size = button.w
    spacing = 5
    max_width = 400

    buttons_per_row = max_width // (button_size + spacing)

    row = cell_index // buttons_per_row
    col = cell_index % buttons_per_row

    start_x = cat_x + 55

    button.pos = (start_x + col * (button_size + spacing), sub_y - row * (button_size + spacing))

    button.dir = selected['direction']


def category_visual(button):
    button.pos = (button.pos[0], screen.get_height() - 70)
    button.dir = selected['direction']


def subcategory_visual(button):
    cat_index = button.category_index
    sub_index = button.sub_index

    cat_x = cat_index * 70 + 10
    base_y = screen.get_height() - 70

    cat_width = 60
    sub_width = button.w

    offset_x = (cat_width - sub_width) / 2

    button.pos = (cat_x + offset_x, base_y - 50 * (sub_index + 1))

    button.dir = selected['direction']


def mouse_on_button(button):
    return button.hovering()


def mouse_on_any_button():
    for button in button_list:
        if button.hovering() and not should_hide_button(button):
            return True
    return False


def get_button_mouse_on():
    for button in button_list:
        if button.hovering() and not should_hide_button(button):
            return button
    return None


def get_subcategory_name(sub_list):
    for name, value in subcategories.items():
        if value == sub_list:
            return format_cell_name(name)
    return "unknown"


def toggle_running():
    global running, initcells, initstate

    if not running and initstate:
        initcells = {i: cell.copy() for i, cell in cells.items()}

    running = not running


def rebuild_subcategory_buttons():
    global buttons, button_list

    # remove old subcategory buttons
    button_list = [b for b in button_list if b.type != 'subcategory']

    category = categories[selected_category]

    category_x = selected_category * 70 + 10
    bottom_y = screen.get_height() - 70

    for i, sub in enumerate(category['sub']):
        add_button(
            images[sub[0]] or images['notex'],  # uses first cell in subcategory as icon
            (40, 40),
            (category_x, bottom_y - 70 * (i + 1)),
            0,
            lambda i=i: select_subcategory(i),
            get_subcategory_name(sub),
            subcategory_visual
        )
        button_list[-1].type = 'subcategory'
        button_list[-1].category_index = selected_category
        button_list[-1].sub_index = i


def rebuild_cell_buttons():
    global buttons, button_list

    button_list = [b for b in button_list if b.type != 'cell']

    if selected_category is None or selected_subcategory is None:
        return

    sub = categories[selected_category]['sub'][selected_subcategory]

    start_x = selected_category * 70 + 65
    start_y = screen.get_height() - 70 - 50 * (selected_subcategory + 1)

    max_width = 400
    button_size = 40
    spacing = 5

    buttons_per_row = max_width // (button_size + spacing)

    for i, cell_name in enumerate(sub):
        if cell_name == None: continue
        row = i // buttons_per_row
        col = i % buttons_per_row

        x = start_x + col * (button_size + spacing)
        y = start_y - row * (button_size + spacing)

        add_button(
            images[cell_name] or images['notex'],
            (40, 40),
            (x, y),
            0,
            lambda cell_name=cell_name: select_cell(cell_name),
            format_cell_name(cell_name),
            cell_button_visual
        )

        button_list[-1].type = 'cell'
        button_list[-1].cell_name = cell_name
        button_list[-1].cell_index = i


def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def select_cell(cell_name):
    global selectidx

    names = list(celltypes)
    selectidx = names.index(format_cell_name(cell_name))


def select_category(idx):
    global selected_category, selected_subcategory
    selected_category = idx
    selected_subcategory = None
    rebuild_subcategory_buttons()
    rebuild_cell_buttons()


def select_subcategory(idx):
    global selected_subcategory
    selected_subcategory = idx
    rebuild_cell_buttons()


def revert():
    global cells, effects, initstate, running, lerp, eatencells

    running = False
    lerp = 0
    eatencells = {}

    cells = {i: cell.copy() for i, cell in initcells.items()}
    effects = {i: {} for i in cells}

    initstate = True


def set_init_state():
    global initstate, initcells
    initcells = {i: cell.copy() for i, cell in cells.items()}
    initstate = True


def in_edit():
    global editing, selected_adjustable_key, dropdown_open
    editing = True
    dropdown_open = False

    data = get_adjustable(selected['cell_name'].lower())
    if data:
        selected_adjustable_key = list(data.keys())[0]


def close_editor():
    global editing, dropdown_open
    editing = False
    dropdown_open = False

def close_menu():
    global menu_open
    menu_open = False

def get_current_adjustable_data():
    return get_adjustable(selected['cell_name'].lower())


def editor_rect():
    return pygame.Rect(0, 0, screen.get_width(), screen.get_height())


def get_editor_rect():
    w = screen.get_width() * 0.6
    h = screen.get_height() * 0.6
    x = (screen.get_width() - w) / 2
    y = (screen.get_height() - h) / 2
    return pygame.Rect(x, y, w, h)

def menu_click(pos):
    global menu_open

    rect = get_editor_rect()

    close_rect = pygame.Rect(rect.right - 35, rect.top + 5, 30, 30)

    if close_rect.collidepoint(pos):
        menu_open = False
        return

    mute_rect = pygame.Rect(rect.left + 30, rect.top + 60, 75, 75)

    if mute_rect.collidepoint(pos):
        toggle_mute()

    toggle_rect = pygame.Rect(rect.left + 30, rect.top + 150, 120, 40)

    if toggle_rect.collidepoint(pos):
        toggle_knights()
        return

def editor_click(pos):
    global selected_adjustable_key, dropdown_open, typing_number, typing_number_with_dot, number_text

    rect = get_editor_rect()
    close_rect = pygame.Rect(rect.right - 35, rect.top + 5, 30, 30)

    if close_rect.collidepoint(pos):
        close_editor()
        return

    data = get_current_adjustable_data()
    if data is None:
        return

    line_x = rect.centerx

    y = rect.top + 60

    for key in data:
        btn = pygame.Rect(rect.left + 30, y, (rect.width / 2) - 60, 35)

        if btn.collidepoint(pos):
            selected_adjustable_key = key
            dropdown_open = False
            return

        y += 45

    if selected_adjustable_key is not None:
        setting = data[selected_adjustable_key]

        if setting[1] == 'bool':
            dropdown_rect = pygame.Rect(line_x + 30, rect.top + 60, 100, 35)
        else:
            dropdown_rect = pygame.Rect(line_x + 30, rect.top + 60, 220, 35)

        if dropdown_rect.collidepoint(pos):
            setting = data[selected_adjustable_key]

            if setting[1] == 'number':
                typing_number = True
                typing_number_with_dot = False
                number_text = str(setting[0])
                return

            if setting[1] == 'number+dot':
                typing_number = False
                typing_number_with_dot = True
                number_text = str(setting[0])
                return

            if setting[1] == 'bool':
                setting[0] = not setting[0]
                typing_number = False
                typing_number_with_dot = False
                dropdown_open = False
                return

            dropdown_open = not dropdown_open
            return

    if dropdown_open:
        setting = data[selected_adjustable_key]

        if setting[1] != 'number' or setting[1] != 'number+dot':
            options = setting[1]
            y = dropdown_rect.bottom

            for option in options:
                option_rect = pygame.Rect(dropdown_rect.x, y, dropdown_rect.width, 35)

                if option_rect.collidepoint(pos):
                    data[selected_adjustable_key][0] = option
                    dropdown_open = False
                    return

                y += 35

    dropdown_open = False

def draw_menu():
    if not menu_open:
        return

    overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    overlay.fill((40, 40, 40, 120))
    screen.blit(overlay, (0, 0))

    rect = get_editor_rect()

    pygame.draw.rect(screen, (80, 80, 80), rect)
    pygame.draw.rect(screen, (70, 70, 70), rect, 4)

    close_rect = pygame.Rect(rect.right - 35, rect.top + 5, 30, 30)
    pygame.draw.rect(screen, (120, 50, 50), close_rect)
    pygame.draw.rect(screen, (90, 30, 30), close_rect, 3)

    x_text = font.render("X", True, (255, 255, 255))
    screen.blit(x_text, (close_rect.x + 7, close_rect.y + 2))

    mute_rect = pygame.Rect(rect.left + 30, rect.top + 30, 75, 75)

    mute_image = images['muted'] if music_muted else images['unmuted']

    screen.blit(
        pygame.transform.scale(mute_image, (75, 75)),
        mute_rect.topleft
    )

    x_text = font.render("Swap CW and CCW Knight textures", True, (255, 255, 255))
    x_text = pygame.transform.scale(x_text, (x_text.get_width()/1.5, x_text.get_height()/1.5))
    screen.blit(x_text, (rect.left + 30, rect.top + 120))

    toggle_rect = pygame.Rect(rect.left + 30, rect.top + 150, 120, 40)

    bg_color = (80, 170, 80) if swap_knights else (120, 120, 120)
    pygame.draw.rect(screen, bg_color, toggle_rect)
    pygame.draw.rect(screen, (60, 60, 60), toggle_rect, 3)

    if swap_knights:
        knob_x = toggle_rect.right - 36
    else:
        knob_x = toggle_rect.left + 4

    knob_rect = pygame.Rect(knob_x, toggle_rect.y + 4, 32, 32)
    pygame.draw.rect(screen, (230, 230, 230), knob_rect)
    pygame.draw.rect(screen, (180, 180, 180), knob_rect, 2)

def draw_editor():
    if not editing:
        return

    overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    overlay.fill((40, 40, 40, 120))
    screen.blit(overlay, (0, 0))

    rect = get_editor_rect()

    pygame.draw.rect(screen, (80, 80, 80), rect)
    pygame.draw.rect(screen, (70, 70, 70), rect, 4)

    close_rect = pygame.Rect(rect.right - 35, rect.top + 5, 30, 30)
    pygame.draw.rect(screen, (120, 50, 50), close_rect)
    pygame.draw.rect(screen, (90, 30, 30), close_rect, 3)

    x_text = font.render("X", True, (255, 255, 255))
    screen.blit(x_text, (close_rect.x + 7, close_rect.y + 2))

    line_x = rect.centerx
    pygame.draw.line(screen, (150, 150, 150), (line_x, rect.top + 50), (line_x, rect.bottom - 20), 2)

    data = get_current_adjustable_data()
    if data is None:
        return

    small_font = pygame.font.Font(resource_path('nokiafcellua.ttf'), 18)

    y = rect.top + 60

    for key in data:
        btn = pygame.Rect(rect.left + 30, y, (rect.width / 2) - 60, 35)

        color = (110, 110, 110)
        if key == selected_adjustable_key:
            color = (140, 140, 140)

        pygame.draw.rect(screen, color, btn)

        text = small_font.render(key, True, (255, 255, 255))
        screen.blit(text, (btn.x + 8, btn.y + 7))

        y += 45

    if selected_adjustable_key is not None:
        current_value = data[selected_adjustable_key][0]
        setting_type = data[selected_adjustable_key][1]

        dropdown_rect = pygame.Rect(line_x + 30, rect.top + 60, 220, 35)

        if setting_type == "bool":
            bg_color = (80, 170, 80) if current_value else (120, 120, 120)

            new_rect = pygame.Rect(line_x + 30, rect.top + 60, 100, 35)

            pygame.draw.rect(screen, bg_color, new_rect)
            pygame.draw.rect(screen, (50, 50, 50), new_rect, 2)

            knob_size = 27

            if current_value:
                knob_x = new_rect.right - knob_size - 4
            else:
                knob_x = new_rect.left + 4

            knob_rect = pygame.Rect(
                knob_x,
                new_rect.y + 4,
                knob_size,
                new_rect.height - 8
            )

            pygame.draw.rect(screen, (230, 230, 230), knob_rect)
            pygame.draw.rect(screen, (180, 180, 180), knob_rect, 2)

        else:
            pygame.draw.rect(screen, (100, 100, 100), dropdown_rect)
            pygame.draw.rect(screen, (50, 50, 50), dropdown_rect, 2)

            display_text = number_text if typing_number or typing_number_with_dot else str(current_value)

            if type(setting_type) is list:
                display_text += " ∨"

            text = small_font.render(display_text, True, (255, 255, 255))
            screen.blit(text, (dropdown_rect.x + 8, dropdown_rect.y + 7))

        if dropdown_open and type(setting_type) is list:
            y = dropdown_rect.bottom

            for option in setting_type:
                option_rect = pygame.Rect(dropdown_rect.x, y, dropdown_rect.width, 35)
                pygame.draw.rect(screen, (90, 90, 90), option_rect)

                option_text = small_font.render(str(option), True, (255, 255, 255))
                screen.blit(option_text, (option_rect.x + 8, option_rect.y + 7))

                y += 45

def open_menu():
    global menu_open
    menu_open = True

def menu_visual(button):
    button.pos = (screen.get_width() - 90, button.pos[1])

add_button(images['mover'] or images['notex'], (75, 75), (10, 10), 0, toggle_running, 'Play (Space)', play_button_visual)
add_button(images['180 rotator'] or images['notex'], (75, 75), (10, 90), 0, revert, 'Revert')
button_list[-1].type = 'revert'
add_button(images['generator'] or images['notex'], (75, 75), (90, 90), 0, set_init_state, 'Set Initial State')
button_list[-1].type = 'revert'
add_button(edit_icon, (75, 75), (90, 10), 0, in_edit, 'Edit Cell Properties')
button_list[-1].type = 'edit'
add_button(images['menu'] or images['notex'], (75, 75), (90, 10), 0, open_menu, 'Menu', update_visual=menu_visual)
button_list[-1].type = 'menu'

for i, category in enumerate(categories):
    add_button(category['texture'], (60, 60), (i * 70 + 10, 10), 0, lambda i=i: select_category(i), category['name'],
               category_visual)


def should_hide_button(button):
    if getattr(button, 'type', None) == 'revert' and initstate:
        return True

    if getattr(button, 'type', None) == 'edit' and not edit_button:
        return True

    if getattr(button, 'type', None) == 'menu' and menu_open:
        return True

    return False


def draw_buttons():
    for button in button_list:
        if should_hide_button(button):
            continue

        if getattr(button, 'type', None) == 'cell':
            button.image = images[visual_cell_name(button.cell_name)] or images['notex']

        button.draw()


def draw_desc():
    if not mouse_on_any_button(): return

    button = get_button_mouse_on()
    x, y = pygame.mouse.get_pos()

    # BIG TEXT (name)
    bigtext = font.render(button.name, True, (255, 255, 255))
    title_w, title_h = font.size(button.name)

    # SMALL TEXT (description)
    desc_lines = []
    small_font = pygame.font.Font(resource_path('nokiafcellua.ttf'), 16)

    if button.type == 'cell':
        desc = celltypes[format_cell_name(button.cell_name)]['desc']
        desc_lines = wrap_text(desc, small_font, 400)

    # CALCULATE BOX SIZE
    if button.type == 'cell':
        width = max(title_w, small_font.size(desc_lines[0])[0]) + 10
    else:
        width = title_w + 10

    height = title_h + 10

    for line in desc_lines:
        height += small_font.size(line)[1]

    height += 5 if desc_lines else 0

    screen_height = screen.get_height()
    if y + height > screen_height:
        y = screen_height - height

    # DRAW BOX
    pygame.draw.rect(screen, (70, 70, 70), (x, y, width, height))
    pygame.draw.rect(screen, (60, 60, 60), (x, y, width, height), 3)

    # DRAW TITLE
    screen.blit(bigtext, (x + 5, y + 5))

    # DRAW DESCRIPTION
    offset_y = y + 5 + title_h + 5

    for line in desc_lines:
        text_surface = small_font.render(line, True, (200, 200, 200))
        screen.blit(text_surface, (x + 5, offset_y))
        offset_y += small_font.size(line)[1]


def draw_all_cells():
    global effects
    for i in eatencells:
        cell = eatencells[i]
        if cell.olddirection == 3 and cell.direction == 0:
            cell.olddirection = -1
        if cell.olddirection == 0 and cell.direction == 3:
            cell.olddirection = 4
        if cell.olddirection == 2 and cell.direction == 0:
            cell.olddirection = -2
        draw_eaten_cell(
            cell.name,
            anim.lerp_position(cell.oldx, cell.x, lerp),
            anim.lerp_position(cell.oldy, cell.y, lerp),
            anim.lerp_position(cell.olddirection, cell.direction, lerp),
        )
    for i in cells:
        cell = cells[i]
        if cell.olddirection == 3 and cell.direction == 0:
            cell.olddirection = -1
        if cell.olddirection == 0 and cell.direction == 3:
            cell.olddirection = 4
        if cell.olddirection == 2 and cell.direction == 0:
            cell.olddirection = -2
        if cell.olddirection == 3 and cell.direction == 0.5:
            cell.olddirection = -1
        if cell.olddirection == 0 and cell.direction == 3.5:
            cell.olddirection = 4
        if cell.olddirection == 3.5 and cell.direction == 0.5:
            cell.olddirection = -0.5
        if cell.olddirection == 3.5 and cell.direction == 0:
            cell.olddirection = -0.5
        draw_cell(
            cell.name,
            anim.lerp_position(cell.oldx, cell.x, lerp),
            anim.lerp_position(cell.oldy, cell.y, lerp),
            anim.lerp_position(cell.olddirection, cell.direction, lerp),
        )
        draw_func = get_tag_raw(cell.name, 'draw_properties')

        if draw_func is not None:
            draw_cell_copy = cell.copy()
            draw_cell_copy.x = anim.lerp_position(cell.oldx, cell.x, lerp)
            draw_cell_copy.y = anim.lerp_position(cell.oldy, cell.y, lerp)
            draw_cell_copy.direction = anim.lerp_position(cell.olddirection, cell.direction, lerp)

            draw_func(draw_cell_copy, cell.properties)
        if i in effects:
            for effect in effects[i].values():
                draw_cell(
                    effect,
                    anim.lerp_position(cell.oldx, cell.x, lerp),
                    anim.lerp_position(cell.oldy, cell.y, lerp),
                    0,
                )


def draw_ghost_cell(cell_name, x, y, direction):
    size = int(image_size * zoom)

    draw_name = visual_cell_name(cell_name.lower())

    transformed_image = pygame.transform.scale(
        images[draw_name] or images['notex'],
        (size, size)
    )

    rotated_image = pygame.transform.rotate(
        transformed_image,
        direction * -90
    )

    rotated_image.set_alpha(128)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    rect = transformed_image.get_rect(topleft=(screen_x, screen_y))
    rotated_rect = rotated_image.get_rect(center=rect.center)

    screen.blit(rotated_image, rotated_rect)



def get_adjacent_ids(x, y, dist=1, surrounding=False):
    if not surrounding: return {0: get_cell_idx_at_pos(x + dist, y), 1: get_cell_idx_at_pos(x, y + dist), 2: get_cell_idx_at_pos(x - dist, y), 3: get_cell_idx_at_pos(x, y - dist)}
    return {
        0: get_cell_idx_at_pos(x + dist, y),
        0.5: get_cell_idx_at_pos(x + dist, y + dist),
        1: get_cell_idx_at_pos(x, y + dist),
        1.5: get_cell_idx_at_pos(x - dist, y + dist),
        2: get_cell_idx_at_pos(x - dist, y),
        2.5: get_cell_idx_at_pos(x - dist, y - dist),
        3: get_cell_idx_at_pos(x, y - dist),
        3.5: get_cell_idx_at_pos(x + dist, y - dist)
    }

def move_or_delete(cell_id, newpos):
    if out_of_bounds(newpos[0], newpos[1]):
        x, y = cells[cell_id].x, cells[cell_id].y
        cell_delete(cell_id, newpos[0], newpos[1])
        return True

    cells[cell_id].x = newpos[0]
    cells[cell_id].y = newpos[1]
    return True


def rotate_cell_id(idx, amt, force_dir):
    if idx is not None:
        if blocks_side(cells[idx], force_dir):
            return

        if is_unbreakable(cells[idx].name, 'rotate', to_side(force_dir, cells[idx].direction)):
            return

        cells[idx].direction = (cells[idx].direction + amt) % 4


def give_effect(id, effect, side):
    if id is not None and effect not in effects[id]:
        if is_unbreakable(cells[id].name, effect, side):
            return
        if effect == 'enabled': take_effect(id, 'disabled', side)
        effects[id][len(effects[id]) + 1] = effect


def take_effect(id, effect, side):
    if id is None: return
    if is_unbreakable(cells[id].name, 'take' + effect, side): return
    for key, value in list(effects[id].items()):
        if value == effect:
            effects[id].pop(key)


def has_effect(id, effect):
    return id in effects and effect in effects[id].values()


def to_side(fdir, direction):
    return (fdir - direction + 2) % 4


def get_move_dir(direction):
    direction = direction % 4

    lower = int(direction * 2) / 2
    upper = (lower + 0.5) % 4

    percent_to_upper = (direction - lower) / 0.5

    global ticks

    if (ticks % 100) / 100 < percent_to_upper:
        return upper
    else:
        return lower

def step_forward(x, y, direction, loopcount=0, startidx=None):
    if startidx is None:
        startidx = get_cell_idx_at_pos(x, y)

    if startidx == get_cell_idx_at_pos(x, y):
        loopcount += 1

    if loopcount > 5:
        return {'x': x, 'y': y, 'direction': direction, 'rotated': False, 'looped': True}

    x += direction.x
    y += direction.y

    idx = get_cell_idx_at_pos(x, y)

    if idx is None:
        return {'x': x, 'y': y, 'direction': direction, 'rotated': False, 'looped': False}

    cell = cells[idx]
    side = to_side(vec_to_dir(direction), cell.direction)

    if cell.name == 'straight diverger':
        if side % 2 == 0:
            return step_forward(x, y, direction, loopcount, startidx)

    elif cell.name == 'curve diverger':
        if side == 0:
            result = step_forward(x, y, direction.rotate(-1), loopcount, startidx)
            result['rotated'] = True
            return result

        if side == 1:
            result = step_forward(x, y, direction.rotate(1), loopcount, startidx)
            result['rotated'] = True
            return result

    return {'x': x, 'y': y, 'direction': direction, 'rotated': False, 'looped': False}

def go_through_wires(x, y, direction, visited=None):
    if visited is None:
        visited = set()

    dir_num = direction % 4
    move_vec = dir_to_vec2(dir_num)

    x += move_vec.x
    y += move_vec.y

    while True:
        idx = get_cell_idx_at_pos(x, y)

        if idx is None:
            return {'x': x, 'y': y, 'direction': dir_num}

        if idx in visited:
            return {'x': x, 'y': y, 'direction': dir_num}

        visited.add(idx)

        cell = cells[idx]
        wiring = get_wiring(cell.name)

        if wiring is None:
            return {'x': x, 'y': y, 'direction': dir_num}

        enter_side = to_side(dir_num, cell.direction)

        if enter_side not in wiring:
            return {'x': x, 'y': y, 'direction': dir_num}

        exits = wiring.copy()
        exits.remove(enter_side)

        if len(exits) == 0:
            return {'x': x, 'y': y, 'direction': dir_num}

        exit_side = exits[0]
        dir_num = (exit_side + cell.direction) % 4

        move_vec = dir_to_vec2(dir_num)
        x += move_vec.x
        y += move_vec.y

def get_math_value(cell_id, reading_dir, visited=None):
    if visited is None:
        visited = set()

    if cell_id is None or cell_id not in cells:
        return 0

    if cell_id in visited:
        return 0

    visited.add(cell_id)

    cell = cells[cell_id]

    wiring = get_wiring(cell.name)

    if wiring is not None:
        side = to_side(reading_dir, cell.direction)

        if side in wiring:
            go_through = go_through_wires(cell.x, cell.y, reading_dir, visited)

            return get_math_value(
                get_cell_idx_at_pos(go_through['x'], go_through['y']),
                go_through['direction'],
                visited
            )

        return 0

    if cell.name == 'number':
        return cell.properties.get('Value', 0)

    if cell.name == 'add':
        if cell.direction != (reading_dir + 2) % 4:
            return 0

        top_data = go_through_wires(cell.x, cell.y, cell.direction - 1)
        bottom_data = go_through_wires(cell.x, cell.y, cell.direction + 1)

        top_id = get_cell_idx_at_pos(top_data['x'], top_data['y'])
        bottom_id = get_cell_idx_at_pos(bottom_data['x'], bottom_data['y'])

        return (
            get_math_value(top_id, cell.direction - 1, visited.copy()) +
            get_math_value(bottom_id, cell.direction + 1, visited.copy())
        )

    return 0

def get_pos_infront_of_pos(pos, direction):
    direction = get_move_dir(direction)
    x, y = pos

    moves = {
        0: (1, 0),  # right
        0.5: (1, 1),  # down-right
        1: (0, 1),  # down
        1.5: (-1, 1),  # down-left
        2: (-1, 0),  # left
        2.5: (-1, -1),  # up-left
        3: (0, -1),  # up
        3.5: (1, -1),  # up-right
    }

    dx, dy = moves[direction]
    return x + dx, y + dy

def dir_to_vec2(dir):
    moves = {
        0: (1, 0),  # right
        0.5: (1, 1),  # down-right
        1: (0, 1),  # down
        1.5: (-1, 1),  # down-left
        2: (-1, 0),  # left
        2.5: (-1, -1),  # up-left
        3: (0, -1),  # up
        3.5: (1, -1),  # up-right
    }
    return Vec2(moves[dir%4][0],moves[dir%4][1])

def vec_to_dir(vec):
    raw = (math.atan2(vec.y, vec.x) / (math.pi / 2)) % 4

    snapped = round(raw * 2) / 2

    if snapped == int(snapped):
        snapped = int(snapped)

    return snapped

def cell_delete(idx, trashx, trashy):
    if idx is None:
        return

    x, y = cells[idx].x, cells[idx].y

    eatencell = cells[idx].copy()
    eatencell.oldx = x
    eatencell.oldy = y
    eatencell.x = trashx
    eatencell.y = trashy

    eatencells[len(eatencells) + 1] = eatencell
    cells.pop(idx)


def blocks_side(cell, move_dir):
    sides = ['Right', 'Down', 'Left', 'Up']

    if isinstance(move_dir, Vec2):
        move_dir = vec_to_dir(move_dir)

    side_index = int((move_dir + 2 - cell.direction) % 4)
    side_name = sides[side_index]

    return cell.properties.get(side_name, 'None') == 'Wall'


def swap_cells(a_pos, b_pos, a_side, b_side):
    a_id = get_cell_idx_at_pos(a_pos[0], a_pos[1])
    b_id = get_cell_idx_at_pos(b_pos[0], b_pos[1])

    if a_id is None and b_id is not None:
        b = cells[b_id]
        b.x, b.y = a_pos[0], a_pos[1]
        return True

    if a_id is not None and b_id is None:
        a = cells[a_id]
        a.x, a.y = b_pos[0], b_pos[1]
        return True

    if a_id is None and b_id is None:
        return False

    a = cells[a_id]
    b = cells[b_id]

    # wall-side blocking
    if blocks_side(a, a_side):
        return False

    if blocks_side(b, b_side):
        return False

    # normal unbreakable swap blocking
    if is_unbreakable(a.name, 'swap', a_side):
        return False

    if is_unbreakable(b.name, 'swap', b_side):
        return False

    a.x, b.x = b.x, a.x
    a.y, b.y = b.y, a.y

    return True

def update():
    global effects, ticks, initstate, updated
    updated.clear()
    initstate = False
    cell_list = list(cells.items())

    for i, cell in cell_list:
        if cells[i].name == 'disabler':
            for k, id in enumerate(get_adjacent_ids(cells[i].x, cells[i].y)):
                if id is None: continue
                give_effect(id, 'disabled', to_side(k, cells[id].direction))

    for i, cell in cell_list:
        if cells[i].name == 'enabler':
            for k, id in enumerate(get_adjacent_ids(cells[i].x, cells[i].y)):
                if id is None: continue
                give_effect(id, 'enabled', to_side(k, cells[id].direction))

    cell_list = [
        (i, cell)
        for i, cell in cell_list
        if not has_effect(i, 'disabled')
    ]

    UPDATE_DIRS = [0, 0.5, 2, 2.5, 1, 1.5, 3, 3.5]

    def sort_directional_cells(items, direction):
        direction %= 4
        if direction == 0:
            items.sort(key=lambda item: item[1].x)
        elif direction == 2:
            items.sort(key=lambda item: item[1].x, reverse=True)
        elif direction == 3:
            items.sort(key=lambda item: item[1].y, reverse=True)
        elif direction == 1:
            items.sort(key=lambda item: item[1].y)

    def run_directional_updates(cell_list, cell_names, update_func, axis=None, reverse=False):
        if axis == 'h':
            group = []

            for i, cell in cell_list:
                if i in cells and cells[i].name in cell_names and (cells[i].direction == 0 or cells[i].direction == 2):
                    group.append((i, cells[i]))

            sort_directional_cells(group, 0 if reverse else 2)

            for i, cell in group:
                if i in cells:
                    if i in updated: continue
                    update_func(i, cell, cell.direction)
                    updated.add(i)
            return
        if axis == 'v':
            group = []

            for i, cell in cell_list:
                if i in cells and cells[i].name in cell_names and (cells[i].direction == 1 or cells[i].direction == 3):
                    group.append((i, cells[i]))

            sort_directional_cells(group, 1 if reverse else 3)

            for i, cell in group:
                if i in cells:
                    if i in updated: continue
                    update_func(i, cell, cell.direction)
                    updated.add(i)
            return
        for direction in UPDATE_DIRS:
            group = []

            for i, cell in cell_list:
                if i in cells and cells[i].name in cell_names and cells[i].direction == direction:
                    group.append((i, cells[i]))

            sort_directional_cells(group, direction if reverse else direction+2)

            for i, cell in group:
                if i in cells:
                    if i in updated: continue
                    update_func(i, cell, direction)
                    updated.add(i)

    def update_mover(i, cell, direction):
        success = False

        if cell.name == 'mover':
            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]

#        if cell.name == 'cw veerer':
#            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
#            if not success:
#                rotate_cell_id(i, 1, 0)

#        if cell.name == 'ccw veerer':
#            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
#            if not success:
#                rotate_cell_id(i, -1, 0)

#        if cell.name == 'cw half veerer':
#            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
#            if not success:
#                rotate_cell_id(i, 0.5, 0)

#        if cell.name == 'ccw half veerer':
#            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
#            if not success:
#                rotate_cell_id(i, -0.5, 0)

        if cell.name == 'super mover':
            success = True
            while success and i in cells:
                success = push_cell(i, dir_to_vec2(cell.direction), omega, 999, {'lastcell': i})[0]

        elif cell.name == 'diagonal mover':
            success = push_cell(i, dir_to_vec2(cell.direction - 0.5), 1, 999, {'lastcell': i})[0]

        elif cell.name == 'leaper':
            v = dir_to_vec2(cell.direction)
            success = push_cell(i, Vec2(v.x * 2, v.y * 2), 1, 999, {'lastcell': i})[0]

        elif cell.name == 'cw knight':
            v = Vec2(2, 1)
            success = push_cell(i, v.rotate(cell.direction), 1, 999, {'lastcell': i})[0]

        elif cell.name == 'ccw knight':
            v = Vec2(2, -1)
            success = push_cell(i, v.rotate(cell.direction), 1, 999, {'lastcell': i})[0]

        elif cell.name == 'adjustable mover':
            prop = cell.properties
            v = Vec2(prop['Run'], -prop['Rise']).rotate(cell.direction)
            for step in range(prop['Speed']):
                if ticks%prop['Delay'] != 0:
                    break
                if i not in cells:
                    break
                success = push_cell(i, v, prop['Bias'], 999, {'lastcell': i})[0]
                if not success:
                    break

        elif cell.name == 'veerer':
            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]

            if not success:
                prop = cell.properties

                rotation = prop.get('Rotation', 0)
                random_rotation = prop.get('Random', False)

                if random_rotation:
                    rotation *= random.choice([-1, 1])

                rotate_cell_id(i, rotation, 0)

    def update_gear(i, cell):
        neighbors = get_adjacent_ids(cell.x, cell.y, surrounding=True)

        offset = 1
        if cell.name == 'ccw gear':
            offset = -1
        if cell.name == '180 gear':
            offset = 2
        if cell.name == 'random gear':
            offset = random.randint(0, 1) * 2 - 1
        if cell.name == 'cw half gear':
            offset = 0.5
        if cell.name == 'ccw half gear':
            offset = -0.5
        if cell.name == 'random half gear':
            offset = (random.randint(0, 1) * 2 - 1) / 2
        if cell.name == 'cw fast gear':
            offset = 1.5
        if cell.name == 'ccw fast gear':
            offset = -1.5
        if cell.name == 'jam':
            return
        if cell.name == 'random fast gear':
            offset = (random.randint(0, 1) * 2 - 1) * (3/2)

        cx, cy = cell.x, cell.y

        target_positions = {
            0:(cx + 1, cy),  # right
            0.5: (cx + 1, cy + 1),  # rightdown
            1:(cx, cy + 1),  # down
            1.5: (cx - 1, cy + 1),  # downleft
            2:(cx - 1, cy),  # left
            2.5: (cx - 1, cy - 1),  # leftup
            3:(cx, cy - 1),  # up
            3.5: (cx + 1, cy - 1),  # upright
        }

        moves = []

        for dir, neighbor_id in neighbors.items():
            dir = (dir+cell.direction)%4
            neighbor_id = get_adjacent_ids(cell.x, cell.y, surrounding=True)[dir]
            if neighbor_id is None:
                continue

            name = cells[neighbor_id].name

            if blocks_side(cells[neighbor_id], dir):
                return

            if is_unbreakable(name, 'swap', to_side(dir, cells[neighbor_id].direction)):
                return

            if name in subcategories['gears']:
                return

        rotate_cell_id(i, offset, 0)

        for dir, neighbor_id in neighbors.items():
            dir = (dir+cell.direction)%4
            neighbor_id = get_adjacent_ids(cell.x, cell.y, surrounding=True)[dir]
            if neighbor_id is None:
                continue

            target_dir = (dir + offset) % 4
            moves.append((neighbor_id, target_positions[target_dir]))

        for dir, (neighbor_id, pos) in enumerate(moves):
            cells[neighbor_id].x = pos[0]
            cells[neighbor_id].y = pos[1]
            rotate_cell_id(neighbor_id, offset, dir)

    def update_puller(i, cell, direction):
        global undocells, cells
        if cell.name == 'super puller':
            success = True

            while success and i in cells:
                success = pull_cell(
                    i,
                    dir_to_vec2(cell.direction),
                    omega,
                    999,
                    {'lastcell': i}
                )[0]
        if cell.name == 'puller':
            pull_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})
        elif cell.name == 'advancer':
            frontpos = get_pos_infront_of_pos((cell.x, cell.y), cell.direction)
            frontid = get_cell_idx_at_pos(frontpos[0], frontpos[1])

            undocells = {id: c.copy() for id, c in cells.items()}

            if frontid is not None:
                push_cell(frontid, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})

            success, force = pull_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})

            if not success:
                cells = undocells
        elif cell.name == 'diagonal puller':
            pull_cell(i, dir_to_vec2(cell.direction - 0.5), 1, 999, {'lastcell': i})
        elif cell.name == 'leap puller':
            pull_cell(i, dir_to_vec2(cell.direction).multiply(2), 1, 999, {'lastcell': i})

    def update_generator(i, cell, direction):
        gx, gy = cell.x, cell.y

        rotations = get_tag(cell.name, 'gen_rotate')
        if rotations is None:
            rotations = [0]
        elif isinstance(rotations, int) or isinstance(rotations, float):
            rotations = [rotations]

        move_offset = get_tag(cell.name, 'gen_move') or 0

        output_offsets = get_tag(cell.name, 'gen_output_offset')
        if output_offsets is None:
            output_offsets = [0]
        elif isinstance(output_offsets, int) or isinstance(output_offsets, float):
            output_offsets = [output_offsets]

        input_dir = (direction + move_offset) % 4

        backward = step_forward(gx, gy, dir_to_vec2((input_dir + 2) % 4))
        behindpos = (backward['x'], backward['y'])
        behind_id = get_cell_idx_at_pos(behindpos[0], behindpos[1])

        if behind_id is None:
            return

        behindside = to_side(vec_to_dir(backward['direction']), cells[behind_id].direction)

        cellbehind = cells[behind_id].copy()

        genas = get_tag(cellbehind.name, 'gen_as', cellbehind, behindside)

        if genas is None:
            genas = cellbehind.name

        if genas == 'BLOCK_GENERATOR':
            return

        gen_props = cellbehind.properties

        if isinstance(genas, dict):
            gen_props = genas.get('properties', gen_props)
            genas = genas.get('name', cellbehind.name)

        genz = genas == 0

        for rot in rotations:
            for output_offset in output_offsets:
                out_dir = (direction + move_offset + output_offset + rot) % 4

                forward = step_forward(gx, gy, dir_to_vec2(out_dir))
                frontpos = (forward['x'], forward['y'])
                front_id = get_cell_idx_at_pos(frontpos[0], frontpos[1])
                physical_type = get_tag(cell.name,'physical')

                if front_id is None or push_cell(front_id, dir_to_vec2(out_dir), 1, 999, {'lastcell': front_id})[0]:
                    if not genz:
                        add_cell(
                            genas,
                            frontpos[0],
                            frontpos[1],
                            cellbehind.direction + move_offset + rot,
                            gx,
                            gy,
                            cellbehind.direction,
                            properties=gen_props
                        )
                elif physical_type == 'physical' and push_cell(i, dir_to_vec2((cell.direction+2)%4), 1, 999, {'lastcell': i})[0]:
                    gx, gy = cell.x, cell.y
                    forward = step_forward(gx, gy, dir_to_vec2(out_dir))
                    frontpos = (forward['x'], forward['y'])
                    backward = step_forward(gx, gy, dir_to_vec2((input_dir + 2) % 4))
                    behindpos = (backward['x'], backward['y'])
                    behind_id = get_cell_idx_at_pos(behindpos[0], behindpos[1])
                    cellbehind = cells[behind_id].copy()
                    if not genz:
                        add_cell(
                            genas,
                            frontpos[0],
                            frontpos[1],
                            cellbehind.direction + move_offset + rot,
                            gx,
                            gy,
                            cellbehind.direction,
                            properties=gen_props
                        )

    def update_mirror(i, cell, direction):
        x, y = cell.x, cell.y

        behindpos = get_pos_infront_of_pos((x, y), (direction + 2) % 4)
        frontpos = get_pos_infront_of_pos((x, y), direction)

        front_id = get_cell_idx_at_pos(frontpos[0], frontpos[1])
        behind_id = get_cell_idx_at_pos(behindpos[0], behindpos[1])

        if front_id is not None and cells[front_id].name == 'mirror':
            if same_axis(cells[front_id].direction, cell.direction):
                return

        if behind_id is not None and cells[behind_id].name == 'mirror':
            if same_axis(cells[behind_id].direction, cell.direction):
                return

        swap_cells(
            frontpos,
            behindpos,
            to_side(direction, cell.direction),
            to_side(direction + 2, cell.direction)
        )

    def run_position_updates(cell_list, cell_names, update_func):
        group = []

        for i, cell in cell_list:
            if i in cells and cells[i].name in cell_names:
                group.append((i, cells[i]))

        # scan order: left-to-right, top-to-bottom
        group.sort(key=lambda item: (item[1].y, item[1].x))

        for i, cell in group:
            if i in cells:
                if i in updated: continue
                update_func(i, cell)
                updated.add(i)

    def update_rotator(i, cell):
        amounts = {
            'cw rotator': 1,
            'ccw rotator': -1,
            '180 rotator': 2,
            'random rotator': random.randint(0, 1) * 2 - 1,
            'cw half rotator': 0.5,
            'ccw half rotator': -0.5,
            'random half rotator': (random.randint(0, 1) * 2 - 1)/2,
            'cw fast rotator': 1.5,
            'ccw fast rotator': -1.5,
            'random fast rotator': (random.randint(0, 1) * 2 - 1) * (3/2),
        }

        amt = amounts[cell.name]
        sides = {
            0: 'Right',
            0.5: 'RightDown',
            1: 'Down',
            1.5: 'DownLeft',
            2: 'Left',
            2.5: 'LeftUp',
            3: 'Up',
            3.5: 'UpRight',
        }

        for k, id in enumerate(get_adjacent_ids(cell.x, cell.y, 1)):
            k = (k+cell.direction)%4
            id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
            if id is None:
                continue

            side_index = (to_side(k, cell.direction) + 2) % 4
            side_name = sides[side_index]

            side_state = cell.properties.get(side_name, 'None')

            # if side has Push/Wall/etc, rotator does NOT work there
            if side_state != 'None':
                continue

            rotate_cell_id(id, amt, k)

    def update_repulsor(i, cell):
        for k, id in enumerate(get_adjacent_ids(cell.x, cell.y, 1)):
            k = (k+cell.direction)%4
            id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
            if id is None:
                continue

            push_cell(id, dir_to_vec2(k), 1, 999, {'lastcell': id})

    def update_impulsor(i, cell):
        for k, id in enumerate(get_adjacent_ids(cell.x, cell.y, 2)):
            k = (k+cell.direction)%4
            id = get_adjacent_ids(cell.x, cell.y, 2, surrounding=True)[k]
            if id is None:
                continue

            pull_cell(id, dir_to_vec2((k + 2) % 4), 1, 999, {'lastcell': id})

    def update_math(i, cell, direction):
        front_data = go_through_wires(cell.x, cell.y, cell.direction)
        top_data = go_through_wires(cell.x, cell.y, cell.direction - 1)
        bottom_data = go_through_wires(cell.x, cell.y, cell.direction + 1)

        frontid = get_cell_idx_at_pos(front_data['x'], front_data['y'])
        topid = get_cell_idx_at_pos(top_data['x'], top_data['y'])
        bottomid = get_cell_idx_at_pos(bottom_data['x'], bottom_data['y'])

        front = cells.get(frontid)

        topval = get_math_value(topid, cell.direction - 1)
        botval = get_math_value(bottomid, cell.direction + 1)

        if cell.name == 'add':
            answer = topval + botval
        else:
            return
        
        front.properties['Value'] = answer


    run_directional_updates(cell_list, ['add'], update_math, reverse=True)
    run_directional_updates(cell_list, ['mirror'], update_mirror, 'h')
    run_directional_updates(cell_list, ['mirror'], update_mirror, 'v')
    run_directional_updates(cell_list, subcategories['generators'], update_generator)
    run_position_updates(cell_list, subcategories['rotators'], update_rotator)
    run_position_updates(cell_list, subcategories['gears'], update_gear)
    run_position_updates(cell_list, ['impulsor'], update_impulsor)
    run_position_updates(cell_list, ['repulsor'], update_repulsor)
    run_directional_updates(cell_list, ['super puller'], update_puller)
    run_directional_updates(cell_list, ['puller', 'diagonal puller', 'leap puller', 'advancer'], update_puller)
    run_directional_updates(cell_list, ['super mover'], update_mover)
    run_directional_updates(cell_list, ['mover', 'diagonal mover', 'leaper', 'cw knight', 'ccw knight', 'adjustable mover', 'veerer'], update_mover)
    ticks += 1


def reset_cells():
    global eatencells, effects
    cell_list = list(cells.items())

    eatencells = {}
    effects = {i: {} for i in cells}

    for i, cell in cell_list:
        if i in cells:
            cell.oldx = cell.x
            cell.oldy = cell.y
            cell.olddirection = cell.direction

def same_vec(a, b):
    return a.x * b.y == a.y * b.x and (a.x * b.x + a.y * b.y) > 0

def opposite_vec(a, b):
    return a.x * b.y == a.y * b.x and (a.x * b.x + a.y * b.y) < 0

def push_cell(cell_id, direction, force, depth, data={}):
    if data is None:
        data = {}

    dir_num = vec_to_dir(direction)

    if depth <= 0:
        return False, force

    if direction == Vec2(0, 0):
        return True, force

    cell = cells.get(cell_id)
    if cell is None:
        return True, force

    lastcellid = get_cell_idx_at_pos(cells[data['lastcell']].x, cells[data['lastcell']].y)

    x, y = cell.x, cell.y
    forward = step_forward(x, y, direction)
    newpos = (forward['x'], forward['y'])

    if newpos == (cell.x, cell.y):
        cell.direction = vec_to_dir(forward['direction'])
        direction = forward['direction']
        newpos = get_pos_infront_of_pos((cell.x, cell.y), cell.direction)

    new_direction = None

    if forward.get('rotated', False):
        direction = forward['direction']
        new_direction = vec_to_dir(forward['direction'])

    front_id = get_cell_idx_at_pos(newpos[0], newpos[1])

    if blocks_side(cell, dir_num):
        return False, 0

    collide_result = get_tag(cell.name, 'can_collide', cell_id, lastcellid)

    if collide_result is not None:
        return collide_result, force

    if is_unbreakable(cell.name, 'push', to_side(dir_num, cell.direction)):
        return False, 0

    if cell.name == 'resistance':
        if force != 1:
            return False, 0

    if cell.name == 'random push':
        if random.random() < 0.5:
            force = 0

    if cell.name == 'adjustable weight':
        force = max(force - cell.properties['Weight'], 0)

    if cell.name == 'restrictor':
        force = min(force, 1)

    if cell.name == 'compensator':
        force = max(force, 1)

    if cell.name == 'a weight':
        force = force + 'A'

    if cell.name == 'infinite weight':
        force = force - omega

    if cell.name == 'anti infinite weight':
        force = force + omega

    if cell.name == 'infinitesimal weight':
        force = force - eps

    if cell.name == 'anti infinitesimal weight':
        force = force + eps

    if cell.name == 'gold':
        if dir_num != math.floor(dir_num):
            force = 0

    if cell.name == 'lead':
        if dir_num == math.floor(dir_num):
            force = 0

    if cell.name == 'conductance':
        if force == 1:
            return False, 0

    if cell.name == 'weight':
        force = max(force - 1, 0)

    if cell.name == 'anti weight':
        force = force + 1

    if cell.name == 'nano weight':
        if lastcellid == cell_id:
            force = 0

    if cell.name == 'anti nano weight':
        if lastcellid != cell_id:
            force = 0

    if cell.name == 'slide':
        if cell.direction % 2 != dir_num % 2:
            force = 0

    if cell.name == '3-way push':
        if cell.direction == (dir_num + 1) % 4:
            force = 0

    if cell.name == '1-way push':
        if cell.direction != (dir_num + 2) % 4:
            force = 0

    if cell.name == 'bent slide':
        if cell.direction == (dir_num + 1) % 4 or cell.direction == dir_num:
            force = 0

    if front_id is not None:
        front = cells[front_id]
        if front.name == 'mover' or front.name == 'cw veerer' or front.name == 'ccw veerer':
            mover_vec = dir_to_vec2(front.direction)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if front.name == 'adjustable mover':
            mover_vec = dir_to_vec2(front.direction)
            bias = front.properties['Bias']

            if same_vec(mover_vec, direction):
                force += bias

            if opposite_vec(mover_vec, direction):
                force -= bias

        if front.name == 'super mover':
            mover_vec = dir_to_vec2(front.direction)

            if same_vec(mover_vec, direction):
                force += omega

            if opposite_vec(mover_vec, direction):
                force -= omega

        if front.name == 'advancer':
            mover_vec = dir_to_vec2(front.direction)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if front.name == 'diagonal mover':
            mover_vec = dir_to_vec2(front.direction - 0.5)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if front.name == 'cw knight':
            mover_vec = Vec2(2, 1).rotate(front.direction)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if front.name == 'ccw knight':
            mover_vec = Vec2(2, -1).rotate(front.direction)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if front.name == 'leaper':
            mover_vec = Vec2(2, 0).rotate(front.direction * 90)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        success, force = push_cell(front_id, direction, force, depth - 1, {'lastcell': cell_id})

        if not success:
            return False, force

    if force <= 0:
        return False, 0

    if cell_id not in cells:
        return True, force

    if new_direction is not None:
        cells[cell_id].direction = vec_to_dir(direction)
        cells[cell_id].direction = cells[cell_id].direction%4

    move_or_delete(cell_id, newpos)
    return True, force


def pull_cell(cell_id, direction, force, depth, data={}, visited=None):
    def pull_behind(x, y, direction, force, depth, cell_id):
        backward = step_forward(x, y, direction.multiply(-1))
        behindpos = (backward['x'], backward['y'])
        behind_id = get_cell_idx_at_pos(behindpos[0], behindpos[1])

        if behind_id is not None:
            pull_cell(behind_id, direction, force, depth - 1, {'lastcell': cell_id}, visited)

    if visited is None:
        visited = set()

    state = (cell_id, direction.x, direction.y)

    if state in visited:
        return True, force

    visited.add(state)

    dir_num = direction

    if isinstance(direction, Vec2):
        dir_num = vec_to_dir(direction)
    else:
        direction = dir_to_vec2(direction)
    if data is None:
        data = {}

    if depth <= 0:
        return False, force

    cell = cells.get(cell_id)
    if cell is None:
        return True, force

    if is_unbreakable(cells[cell_id].name, 'pull', to_side(dir_num, cells[cell_id].direction)):
        return False, 0

    if blocks_side(cell, dir_num):
        return False, 0

    lastcellid = get_cell_idx_at_pos(cells[data['lastcell']].x, cells[data['lastcell']].y)

    x, y = cell.x, cell.y
    forward = step_forward(x, y, direction)
    newpos = (forward['x'], forward['y'])

    new_direction = None

    if forward.get('rotated', False):
        new_direction = vec_to_dir(forward['direction'])

    if newpos == (cell.x, cell.y):
        cell.direction = vec_to_dir(forward['direction'])
        direction = forward['direction']
        newpos = get_pos_infront_of_pos((cell.x, cell.y), cell.direction)

    frontid = get_cell_idx_at_pos(newpos[0], newpos[1])

    if lastcellid == cell_id and frontid is not None:
        collide_result = get_tag(cells[frontid].name, 'can_collide', frontid, cell_id)

        if collide_result is not None:
            pull_behind(x, y, direction, force, depth, cell_id)
            return collide_result, force

        return False, 0

    collide_result = get_tag(cell.name, 'can_collide', cell_id, lastcellid)

    if collide_result is not None:
        return collide_result, force

    if cell.name == 'random push':
        if random.random() < 0.5:
            force = 0
    if cell.name == 'infinite weight':
        force = force - omega
    if cell.name == 'anti infinite weight':
        force = force + omega
    if cell.name == 'infinitesimal weight':
        force = force - eps
    if cell.name == 'anti infinitesimal weight':
        force = force + eps
    if cell.name == 'adjustable weight':
        force = max(force - cell.properties['Weight'], 0)
    if cell.name == 'gold':
        if dir_num != math.floor(dir_num):
            force = 0
    if cell.name == 'lead':
        if dir_num == math.floor(dir_num):
            force = 0
    if cell.name == 'weight':
        force = max(force - 1, 0)
    if cell.name == 'conductance':
        if force == 1:
            return False, 0
    if cell.name == 'restrictor':
        force = min(force, 1)
    if cell.name == 'compensator':
        force = max(force, 1)
    if cell.name == 'anti weight':
        force = force + 1
    if cell.name == 'nano weight':
        if lastcellid == cell_id:
            force = 0
    if cell.name == 'anti nano weight':
        if lastcellid != cell_id:
            force = 0
    if cell.name == 'slide':
        if (cell.direction) % 2 != (dir_num % 2):
            force = 0
    if cell.name == '3-way push':
        if cell.direction == (dir_num + 1) % 4:
            force = 0
    if cell.name == '1-way push':
        if cell.direction != (dir_num + 2) % 4:
            force = 0
    if cell.name == 'bent slide':
        if cell.direction == (dir_num + 1) % 4 or cell.direction == dir_num:
            force = 0

    backward = step_forward(x, y, direction.multiply(-1))
    behindpos = (backward['x'], backward['y'])
    behind_id = get_cell_idx_at_pos(behindpos[0], behindpos[1])

    print(behindpos, (cell.x, cell.y))

    if behind_id is not None:
        behind = cells[behind_id]

        if behind.name == 'puller':
            mover_vec = dir_to_vec2(behind.direction)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if behind.name == 'super puller':
            mover_vec = dir_to_vec2(behind.direction)

            if same_vec(mover_vec, direction):
                force += omega

            if opposite_vec(mover_vec, direction):
                force -= omega

        if behind.name == 'advancer':
            mover_vec = dir_to_vec2(behind.direction)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if behind.name == 'diagonal puller':
            mover_vec = dir_to_vec2(behind.direction - 0.5)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if behind.name == 'leap puller':
            mover_vec = dir_to_vec2(behind.direction).multiply(2)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if not pull_cell(behind_id, direction, force, depth - 1, {'lastcell': cell_id}, visited)[0]:
            return False, force

    if force <= 0:
        return False, 0

    if cell_id not in cells:
        return True, force

    if new_direction is not None:
        cells[cell_id].direction += new_direction-vec_to_dir(direction)
        cells[cell_id].direction = cells[cell_id].direction % 4

    move_or_delete(cell_id, newpos)
    return True, force


while x:
    global mouse_y, mouse_x
    if running:
        lerp += dt * 7
    else:
        lerp = 0
        reset_cells()
    if lerp >= 1:
        reset_cells()
        if running: update()
        lerp = 0
    mouse_x, mouse_y = pygame.mouse.get_pos()
    mouse_buttons = pygame.mouse.get_pressed()
    place_x = round(((mouse_x - camera_pos['x']) / (image_size * zoom)) - 0.5)
    place_y = round(((mouse_y - camera_pos['y']) / (image_size * zoom)) - 0.5)
    clicking_button = False
    selected['cell_name'] = list(celltypes)[selectidx]
    edit_button = get_adjustable(selected['cell_name'].lower()) is not None
    if mouse_on_any_button():
        clicking_button = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT: x = False
        if event.type == pygame.KEYDOWN:
            if typing_number or typing_number_with_dot:
                if event.key == pygame.K_RETURN:
                    try:
                        data = get_current_adjustable_data()
                        setting_type = data[selected_adjustable_key][1]

                        if setting_type == "number":
                            value = int(number_text)
                        elif setting_type == "number+dot":
                            value = float(number_text)

                        if selected_adjustable_key == 'Delay':
                            value = max(1, value)

                        if selected_adjustable_key == 'Run':
                            value = max(1, value)

                        data[selected_adjustable_key][0] = value
                    except:
                        pass

                    typing_number = False

                elif event.key == pygame.K_BACKSPACE:
                    number_text = number_text[:-1]

                else:
                    keys_allowed = "-0123456789" if typing_number else "-0123456789." if typing_number_with_dot else ""
                    if event.unicode in keys_allowed:
                        number_text += event.unicode
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if editing:
                    editor_click(event.pos)
                    continue
                if menu_open:
                    menu_click(event.pos)
                    continue

                for button in button_list:
                    if button.type == 'revert' and initstate:
                        continue

                    if button.type == 'edit' and not edit_button:
                        continue

                    if mouse_on_button(button):
                        button.click()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                toggle_running()
            if event.key == pygame.K_e:
                selected['direction'] = (selected['direction'] + 1) % 4
            if event.key == pygame.K_q:
                selected['direction'] = (selected['direction'] - 1) % 4
            if event.key == pygame.K_t:
                selected['direction'] = (selected['direction'] + .5) % 4
            if event.key == pygame.K_r:
                selected['direction'] = (selected['direction'] - .5) % 4
        if event.type == pygame.MOUSEWHEEL:
            old_zoom = zoom

            if event.y > 0:
                zoom *= 1.1
            elif event.y < 0:
                zoom /= 1.1

            zoom = max(0.2, min(zoom, 5))

            mouse_x, mouse_y = pygame.mouse.get_pos()

            world_x_before = (mouse_x - camera_pos['x']) / old_zoom
            world_y_before = (mouse_y - camera_pos['y']) / old_zoom

            camera_pos['x'] = mouse_x - world_x_before * zoom
            camera_pos['y'] = mouse_y - world_y_before * zoom
    if mouse_buttons[0]:
        if not editing and not menu_open and not out_of_bounds(place_x, place_y) and not clicking_button:
            if get_cell_idx_at_pos(place_x, place_y) is None:
                add_cell(
                    selected.get('cell_name'),
                    place_x,
                    place_y,
                    selected.get('direction'),
                    properties=get_selected_properties()
                )
            else:
                delete_cell(place_x, place_y)
                add_cell(
                    selected.get('cell_name'),
                    place_x,
                    place_y,
                    selected.get('direction'),
                    properties=get_selected_properties()
                )
    if mouse_buttons[2]:
        idx = get_cell_idx_at_pos(place_x, place_y)
        if idx is not None and not is_border(idx):
            delete_cell(place_x, place_y)
    keys = pygame.key.get_pressed()
    camera_speed = 10
    if keys[pygame.K_w]:
        camera_pos['y'] += camera_speed
    if keys[pygame.K_s]:
        camera_pos['y'] -= camera_speed
    if keys[pygame.K_a]:
        camera_pos['x'] += camera_speed
    if keys[pygame.K_d]:
        camera_pos['x'] -= camera_speed
    screen.fill((10, 10, 10))
    draw_bg()
    draw_all_cells()
    draw_ghost_cell(selected.get('cell_name'), place_x, place_y, selected['direction'])
    draw_ghost_properties(selected.get('cell_name'), place_x, place_y, selected['direction'])
    draw_buttons()
    draw_editor()
    draw_menu()
    draw_desc()
    pygame.display.flip()
    dt_ms = clock.tick(60)
    dt = dt_ms / 1000
pygame.quit()