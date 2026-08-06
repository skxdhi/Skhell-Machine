"""
Skhell Machine — cellular automaton sandbox.

Architecture (incremental cleanup from a pre-OOP codebase):
  cells.py       – Cell data object
  buttons.py     – UI button widget + easing
  anim.py        – simple lerp helper
  registry.py    – cell type descriptions, tags, categories (extracted)
  game_state.py  – GameState owning grid/cells/effects (extracted; migrate call sites over time)
  main.py        – simulation, rendering, input, main loop

Simulation state is still mostly module-level globals for compatibility; new code
should prefer GameState methods (register_cell, add_cell, move_cell_to, …).
"""
import math

import pygame
import sys
import os
import random
import copy
import anim
import buttons
import cells as cells_module
import json
import base64
import zlib
import re
import webbrowser
import urllib.parse
import string


import pyperclip
import sympy as sp

eps = sp.Symbol('eps', positive=True, infinitesimal=True)
omega = 1 / eps


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def check_nines_anywhere(value):
    text_value = f"{value:.15f}"
    pattern = r"^\d+\.\d+9{6}"
    return bool(re.match(pattern, text_value))


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
selectedlayer = None
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
start_tick_queue = []

typing_number, typing_number_with_dot, typing_string = False, False, False
number_text = ""

initstate = True
initcells = {}
initticks = 0

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


def add_queue(queue_type, ticks_until_event, event):
    queue_type.append((ticks_until_event, event))


celltypes = {
    'mover': {'desc': 'Moves forward one space every tick'},
    # 'diagonal mover': {'desc': 'Moves forward one space diagonally every tick'},
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
    'puller': {
        'desc': 'Like the Mover cell except it moves the cells behind it rather than infront, also it cant move if there is something infront of it'},
    'impulsor': {'desc': 'The opposite of a Repulsor, pulls cells towards it rather than pushing them away'},
    # 'diagonal puller': {'desc': 'A Puller that moves forward 1 space diagonally every tick'},
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
    'cw generator': {
        'desc': 'A Generator but the output direction is bent 90 degrees clockwise, and the outputted cell is rotated too'},
    'ccw generator': {
        'desc': 'A Generator but the output direction is bent 90 degrees counterclockwise, and the outputted cell is rotated too'},
    'bi generator': {'desc': 'A CW Generator combined with a CCW Generator, that means it has 2 outputs'},
    'tri generator': {
        'desc': "A Bi Generator combined with a normal Generator, that means it has 3 outputs.. I'm already tired of this"},
    'cw valve generator': {'desc': 'A CW Generator combined with a normal Generator, that means it has 2 outputs'},
    'ccw valve generator': {'desc': 'A CCW Generator combined with a normal Generator, that means it has 2 outputs'},
    # 'diagonal generator': {'desc': 'A Generator but its input and output are diagonal like a Diagonal Mover'},
    'cw skew generator': {'desc': 'A Generator but its output is bent 45 degrees clockwise'},
    'ccw skew generator': {'desc': 'A Generator but its output is bent 45 degrees counterclockwise'},
    'bi skew generator': {
        'desc': 'A CW Skew Generator combined with a CCW Skew Generator, that means it has 2 outputs'},
    'tri skew generator': {
        'desc': 'A Bi Skew Generator combined with a normal Generator, that means it has 3 outputs... OH NOT THIS AGAI-'},
    'ungeneratable': {
        'desc': 'When a Generator tries to generate this cell, nothing happens, but the Generator still pushes the cell infront of it as if it did something'},
    'adjustable weight': {
        'desc': 'A Weight but you can change how much force it takes away, negative numbers means it adds force'},
    'infinite weight': {'desc': 'A Weight that takes away an infinite amount of bias when pushed'},
    'anti infinite weight': {'desc': 'A Weight that adds an infinite amount of bias when pushed'},
    'super mover': {'desc': 'A Mover that moves infinitely fast, with infinite force'},
    'restrictor': {'desc': 'Limits the force pushing it to 1 unit of force'},
    'compensator': {'desc': 'Sets the force pushing it to 1 if the amount of force is less than 1'},
    'super puller': {'desc': 'A Puller that moves infinitely fast, with infinite force'},
    'adjustable mover': {'desc': 'A Mover in which you can change its properties'},
    # 'cw veerer': {'desc': 'A Mover but when it hits a wall it turns 90 degrees clockwise'},
    # 'ccw veerer': {'desc': 'A Mover but when it hits a wall it turns 90 degrees counterclockwise'},
    'number': {'desc': 'Stores a number, can be used to do math'},
    'straight wire': {'desc': 'A Wire, it can be used to connect an output to an input and vice versa'},
    'curve wire': {'desc': 'A Wire, it can be used to connect an output to an input and vice versa'},
    'add': {'desc': 'Outputs the sum of the 2 inputs'},
    'monogeneratable': {'desc': 'When a Generator tries to generate it, it will output Ungeneratable cells instead'},
    'semigeneratable': {'desc': 'Has a 1/2 chance to act like Ungeneratable'},
    'adjustable generatable': {
        'desc': 'When a Generator tries to generate it, it will output a copy of itself but with a count decreased by 1, if the counter is 0 it will act like Ungeneratable'},
    'antigeneratable': {
        'desc': 'When a Generator tries to generate it, nothing happens; think of it as disabling the generator'},
    'strong enemy': {'desc': 'An Enemy but it has two lives'},
    'adjustable enemy': {
        'desc': 'When a cell collides with it, its counter will decrease by 1, if the counter is 1 it will act like an Enemy'},
    'weak enemy': {'desc': 'An Enemy but it doesnt destroy the cell that collided with it, basically a reversed Trash'},
    'physical generator': {
        'desc': 'Like a normal Generator, but when its being blocked by something it moves itself backwards to create space'},
    'cw half rotator': {'desc': 'Rotates adjacent cells 45 degrees clockwise'},
    'ccw half rotator': {'desc': 'Rotates adjacent cells 45 degrees counterclockwise'},
    # 'cw half veerer': {'desc': 'A Mover but when it hits a wall it turns 45 degrees clockwise'},
    # 'ccw half veerer': {'desc': 'A Mover but when it hits a wall it turns 45 degrees counterclockwise'},
    'cw half gear': {'desc': 'Makes surrounding cells orbit around it in a clockwise motion'},
    'ccw half gear': {'desc': 'Makes surrounding cells orbit around it in a counterclockwise motion'},
    'random half gear': {'desc': 'Makes surrounding cells orbit around either clockwise or counterclockwise'},
    'random half rotator': {'desc': 'Rotates adjacent cells 45 degrees clockwise or counterclockwise'},
    'cw fast rotator': {'desc': 'Rotates adjacent cells 135 degrees clockwise'},
    'ccw fast rotator': {'desc': 'Rotates adjacent cells 135 degrees counterclockwise'},
    'cw fast gear': {'desc': 'Makes surrounding cells orbit around it in a clockwise motion 3x faster'},
    'ccw fast gear': {'desc': 'Makes surrounding cells orbit around it in a counterclockwise motion 3x faster'},
    'random fast rotator': {'desc': 'Rotates adjacent cells 135 degrees clockwise or counterclockwise'},
    'random fast gear': {
        'desc': 'Makes surrounding cells orbit around it either clockwise or counterclockwise 3x faster'},
    'veerer': {
        'desc': 'A Mover but when it cannot move it rotates a certain amount, that amount is adjustable with multiples of 0.5, 0.5 means 45 degree rotation, it can also be negative, there is another switch for random rotation'},
    'infinitesimal weight': {
        'desc': 'A Weight that takes away an infinitesimal amount of bias when pushed, an infinitesimal is a number that is bigger than 0 but less that every positive real number'},
    'anti infinitesimal weight': {
        'desc': 'A Weight that adds an infinitesimal amount of bias when pushed, an infinitesimal is a number that is bigger than 0 but less that every positive real number'},
    'subtract': {'desc': 'Outputs the difference the top input and the bottom input'},
    'multiply': {'desc': 'Outputs the product of the 2 inputs'},
    'storage': {
        'desc': 'When a cell moves into it the cell thats already inside gets moved out (if there is one) and the new one comes in'},
    'cross diverger': {'desc': 'Like 2 perpendicular Straight Divergers layered on top of eachother'},
    'ghost': {'desc': 'A Wall combined with an Antigeneratable'},
    'redirector': {'desc': 'Rotates adjacent cells to face its direction'},
    'player': {'desc': 'Use arrow keys to make this cell move in that direction'},
    'stall trash': {
        'desc': 'Like a trash, but whenever a cell goes into it, it will then act like a wall for one tick on the side/corner the cell went in'},
    'flipper': {'desc': 'Flips cells horizontally, vertically, or diagonally based on what axis the flipper is facing'},
    'purple mover': {'desc': 'A Mover but when it cant move it gets deleted'},
    # 'magenta mover': {'desc': 'Deletes cells in front of it, that doesnt include walls because that would be very broken'},
    'rotator mover': {
        'desc': 'A Mover that rotates the cell behind it CCW and the cell in front of it CW, this looks oddly familiar...'},
    'coin': {
        'desc': 'When a cell moves into its position, the coin is deleted and that cells coin count is incremented'},
    'anti coin': {
        'desc': 'When a cell moves into its position, the coin is deleted and that cells coin count is decremented (the coin count can go negative)'},
    'adjustable coin': {'desc': 'A coin worth an adjustable amount, it can be positive or negative'},
    'inertia': {
        'desc': 'When the cell is pushed, it stores that force and moves with that force every tick, it does this until it hits a wall in which it loses all the momentum'},
    'hydra': {'desc': 'A Mover that attempts to split left and right when it hits a wall'},
    'fragile player': {'desc': 'A Player combined with an enemy'},
    'coin diverger': {
        'desc': 'A Cross Diverger that takes a specific amount of coins from whatever enters it, if the cell that crosses has insufficent balance, it acts like a wall.'},
    'explosive trash': {'desc': 'A Trash cell that deletes adjacent cells when something goes inside'},
    'explosive enemy': {'desc': 'A Enemy cell that deletes adjacent cells when it collides with something'},
    'intaker': {'desc': 'Like a one sided Trash that pulls cells into it on that side'},
    'super intaker': {'desc': 'An Intaker that can pull an entire row of cells in one tick'},
    'phantom': {'desc': 'A Trash that cannot be generated'},
    'zombie': {'desc': 'An Enemy that cannot be generated'},
    'bread': {
        'desc': 'Like An Enemy combined with an Adjustable Weight, needs a certain amount of bias to be destroyed'},
    'arrow': {'desc': 'A Pushable that cannot be rotated'},
    'platformer player': {'desc': 'A Player with gravity, like in those cool platformer games'},
    'acid': {'desc': 'A Pushable that deletes the cell in front of it and itself when its pushed'},
    'key': {
        'desc': 'A Collectable that can be put inside of locks with the same id as it, the amount of uses can also be changed'},
    'lock': {
        'desc': 'A Wall that can be opened by keys with the same id as it, the amount of keys it needs can also be changed'},
    'balloon': {'desc': 'A Pushable that gets deleted when its pressed against a wall'},
    'randomer': {'desc': 'Turns into a random cell'},
    'randulsor': {'desc': 'Randomly repulses and impulses in each direction'},
    '0-way push': {'desc': 'Cannot be pushed in any direction'},
    'curve displacer': {'desc': 'A Curve Diverger that doesnt rotate cells that come into it'},
    'diode diverger': {'desc': 'A Straight Diverger that only lets cells pass in one direction'},
    'jelly': {'desc': "Removes its position from the Gear's available neighbors"},
    'electrocutor': {'desc': 'Gives adjacent cells an effect that lets them update multiple times every tick'},
    'sticky': {'desc': 'When moved, makes its neighbors stick to it'},
    'cw mini gear': {'desc': 'A CW Gear that only affects adjacent cells'},
    'crimson': {'desc': 'Infects adjacent cells, cannot infect air'},
    'warped': {'desc': 'Infects diagonal cells, cannot infect air'},
    'corruption': {'desc': 'Infects surrounding cells, cannot infect air'},
    'fungal': {'desc': 'Infects cells that push it'},
    'cw diode diverger': {'desc': 'A Curve Diverger that only lets cells pass in one direction'},
    'ccw diode diverger': {'desc': 'A Curve Diverger that only lets cells pass in one direction'},
    'cw diode displacer': {'desc': 'A Curve Displacer that only lets cells pass in one direction'},
    'ccw diode displacer': {'desc': 'A Curve Displacer that only lets cells pass in one direction'},
    'ccw mini gear': {'desc': 'A CCW Gear that only affects adjacent cells'},
    '180 mini gear': {'desc': 'A 180 Gear that only affects adjacent cells'},
    'random mini gear': {'desc': 'A Random Gear that only affects adjacent cells'},
    '0 rotator': {'desc': 'Rotates adjacent cells 0 degrees, very useful for [INSERT]!'},
    'hyper sticky': {'desc': 'When moved, makes the entire structure stick to it'},
    'anchor': {'desc': 'When rotated, makes the entire structure rotate around it'},
    'hinge': {'desc': 'When rotated, makes the cell in front of it rotate the structure around it instead'},
    'forker': {'desc': 'Like a Diverger with 2 outputs, when a cell comes into its input, 2 are outputted on the indicated sides'},
    'bomb': {'desc': 'When the cell that collected it dies, it destorys adjacent cells too'},
    'single cell generator': {'desc': 'A Generator that cannot generate if there is already a cell in front of it https://www.youtube.com/@SingleCellGenerator'},
    'slope': {'desc': 'A Bidiverger that doesnt rotate cells or forces that go through it'},
    'mega bomb': {'desc': 'Bomb that destroys surrounding cells'},
    'cheese': {'desc': 'When the cell that collected it dies, it drops this item'},
    'toast': {'desc': 'Like a Bread cell but the weight is sqrt(w*h)/10) where w and h are the dimensions of the grid'},
    'euro': {'desc': 'A Coin worth 1.15x a normal one'},
    'lichen': {'desc': 'When a cell pushes it, the lichen will split like a Hydra in that direction'},
    'statifier': {'desc': 'The opposite of electrocutor; Adjacent cells update on the Nth tick, where N is adjustable'},
    'cube roll': {'desc': 'A Player but its cube roll, cube roll is a game by my friend [if ur seeing this his game didnt come out yet]'},
    'bird': {'desc': 'Moves in a zig zag pattern (down, forward, up, forward) it moves normally if its facing up or down though. If it fails to move forward it rotates clockwise'},
    'bee': {'desc': 'A Bird that takes diagonal shortcuts (down-forward, up-forward). It acts normally in all directions'},
    'maker': {'desc': 'A Generator that generates the stored cell inside of it'},
    'self': {'desc': 'When its stored the parent cell sees it as a copy of itself'},
    'googler': {'desc': 'It googles whatever value you put in when a cell goes inside (i recommend you dont trust every Googler you see)'},
}

cell_to_id = {}
id_to_cell = {}

for i, name in enumerate(sorted(celltypes.keys())):
    lower = name.lower()
    cell_to_id[lower] = i
    id_to_cell[i] = lower


def make_save_code():
    data = [
        grid_dimensions[0],
        grid_dimensions[1],
        []
    ]

    for i, cell in cells.items():
        if is_border(i):
            continue

        entry = [
            cell.x,
            cell.y,
            cell.direction,
            cell_to_id[cell.name]
        ]

        if cell.properties:
            entry.append(cell.properties)

        data[2].append(entry)

    raw = json.dumps(data, separators=(',', ':')).encode()
    compressed = zlib.compress(raw, level=9)

    return base64.b64encode(compressed).decode()

def load_every_cell(): # fun
    offset = (5, 5)
    for i, (cell, data) in enumerate(celltypes.items()):
        add_cell(cell, (i%10)+offset[0], math.floor(i/10)+offset[1], 0)

def load_save_code(code):
    global cells
    global grid
    global effects
    global eatencells
    global next_id
    global grid_dimensions
    global border_ids

    compressed = base64.b64decode(code.encode())
    raw = zlib.decompress(compressed).decode()

    width, height, saved_cells = json.loads(raw)

    grid_dimensions = (width, height)

    cells = {}
    grid = {}
    effects = {}
    eatencells = {}
    next_id = 0
    border_ids = set()

    grid_borders(width, height)
    border_ids = set(cells.keys())

    for entry in saved_cells:
        x = entry[0]
        y = entry[1]
        direction = entry[2]
        name = id_to_cell[entry[3]]

        properties = {}
        if len(entry) > 4:
            properties = entry[4]

        add_cell(
            name,
            x,
            y,
            direction,
            properties=properties
        )

    set_init_state()


class Vec2:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def multiply(self, magnitude):
        return Vec2(self.x * magnitude, self.y * magnitude)

    def negate(self):
        return Vec2(-self.x, -self.y)

    def __neg__(self):
        return Vec2(-self.x, -self.y)

    def rotate(self, degrees):
        degrees = degrees * 90
        x = self.x * math.cos(math.radians(-degrees)) + self.y * math.sin(math.radians(-degrees))
        y = -self.x * math.sin(math.radians(-degrees)) + self.y * math.cos(math.radians(-degrees))
        return Vec2(round(x), round(y))

    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __eq__(self, other):
        return isinstance(other, Vec2) and self.x == other.x and self.y == other.y


celltypes = {
    format_cell_name(name): data
    for name, data in celltypes.items()
}


def load_all_images(directory):
    images = {}

    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith((".png", ".jpg", ".jpeg")):
                path = os.path.join(dirpath, filename)

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


def is_unbreakable(cell_name, force_name, side, cell):
    return get_tag(cell_name, 'unbreakable', force_name, side, cell)


def is_nonexistant(cell_name, force_name, side, cell):
    return get_tag(cell_name, 'nonexistant', force_name, side, cell)

def get_default_properties(cell_name):
    """Defaults from adjustable() for this cell type, or {} if none."""
    data = get_adjustable(cell_name)
    if data is None:
        return {}
    return {
        key: value[0]
        for key, value in data.items()
    }

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


def physical_force(force_name):
    return force_name in ['push', 'pull', 'grab']


def trash_unbreakable(force_name, side, cell_id):
    return force_name != 'rotate' and not physical_force(force_name)


def arrow_unbreakable(force_name, side, cell_id):
    return force_name == 'rotate'


def intaker_unbreakable(force_name, side, cell_id):
    return side == 0 and False or force_name != 'rotate' and not physical_force(force_name)


def stall_trash_unbreakable(force_name, side, cell_id):
    return trash_unbreakable(force_name, side, cell_id) or side in (cells[cell_id].properties.get('wall') or set())


def redirector_unbreakable(force_name, side, cell_id):
    return force_name == 'redirect'


def weak_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    cell_delete(cell_id, x, y)

    return True


def normal_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)
    cell_delete(cell_id, x, y)

    return True


def fragile_player_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)
        cell_delete(cell_id, x, y)

    return True


def strong_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    cell_delete(other_cell_id, x, y)
    cells[cell_id].name = 'enemy'

    return True


def adjustable_enemy_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    cell_delete(other_cell_id, x, y)
    cells[cell_id].properties['Count'] -= 1

    if cells[cell_id].properties['Count'] <= 0:
        cell_delete(cell_id, x, y)

    return True


def trash_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)

    return True

def googler_collide(cell_id, other_cell_id, side):
    safe_text = urllib.parse.quote(cells[cell_id].properties['Text'])
    search_url = f"https://google.com/search?q={safe_text}"
    webbrowser.open(search_url)
    return trash_collide(cell_id, other_cell_id, side)

def intaker_collide(cell_id, other_cell_id, side):
    if side != 0: return 'normal'
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)

    return True


def explosive_trash_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)

    for k, id in get_adjacent_ids(x, y).items():
        if id is not None:
            cell_delete(id, x, y)

    return True


def explosive_enemy_collide(cell_id, other_cell_id, side):
    x = cells[cell_id].x
    y = cells[cell_id].y

    if other_cell_id != cell_id:
        cell_delete(other_cell_id, x, y)
    cell_delete(cell_id, x, y)

    for k, id in get_adjacent_ids(x, y).items():
        if id is not None:
            cell_delete(id, x, y)

    return True


def stall_trash_collide(cell_id, other_cell_id, side):
    trash_collide(cell_id, other_cell_id, side)
    cells[cell_id].properties.setdefault('wall', set())
    add_queue(start_tick_queue, 0, lambda c=cell_id: cells[c].properties['wall'].add(side))
    add_queue(start_tick_queue, 1, lambda c=cell_id: cells[c].properties['wall'].discard(side))
    return True


def get_key_id(cell):
    return str(cell.properties.get('ID', 0))


def give_key(holder_id, key_cell):
    if holder_id not in cells:
        return

    key_id = get_key_id(key_cell)
    uses = key_cell.properties.get('Uses', 1)

    holder = cells[holder_id]
    holder.properties.setdefault('keys', {})

    holder.properties['keys'][key_id] = holder.properties['keys'].get(key_id, 0) + uses


def try_unlock(lock_id, opener_id):
    if lock_id not in cells or opener_id not in cells:
        return False

    lock = cells[lock_id]
    opener = cells[opener_id]

    key_id = get_key_id(lock)
    needed = lock.properties.get('Keys Needed', 1)

    opener.properties.setdefault('keys', {})

    if opener.properties['keys'].get(key_id, 0) < needed:
        return False

    opener.properties['keys'][key_id] -= needed

    if opener.properties['keys'][key_id] <= 0:
        opener.properties['keys'].pop(key_id)

    x = lock.x
    y = lock.y

    cell_delete(lock_id, x, y)

    return True


def get_structure(idx):
    if idx is None or idx not in cells:
        return set()

    passed = set()
    to_scan = [idx]

    while to_scan:
        current_id = to_scan.pop()

        if current_id in passed or current_id not in cells:
            continue

        passed.add(current_id)

        cell = cells[current_id]

        for neighbor_id in get_neighbor_ids(cell.x, cell.y).values():
            if (neighbor_id is not None and neighbor_id not in passed):
                to_scan.append(neighbor_id)

    return passed


add_tag('unbreakable', {
    ('wall', True),
    ('trash', trash_unbreakable),
    ('ghost', True),
    ('redirector', redirector_unbreakable),
    ('stall trash', stall_trash_unbreakable),
    ('intaker', intaker_unbreakable),
    ('super intaker', intaker_unbreakable),
    ('phantom', trash_unbreakable),
    ('arrow', arrow_unbreakable),
    ('lock', True),
    ('googler', trash_unbreakable),
})
add_tag('can_collide', {
    ('enemy', normal_collide), ('trash', trash_collide), ('phantom', trash_collide), ('friend', normal_collide),
    ('strong enemy', strong_collide), ('adjustable enemy', adjustable_enemy_collide), ('weak enemy', weak_collide),
    ('stall trash', stall_trash_collide),
    ('fragile player', fragile_player_collide), ('explosive trash', explosive_trash_collide),
    ('explosive enemy', explosive_enemy_collide), ('intaker', intaker_collide), ('super intaker', intaker_collide),
    ('zombie', normal_collide), ('googler', googler_collide),})
add_tag('is_friendly', {('friend', True)})
add_tag('is_unfriendly', {('enemy', True), ('zombie', True), ('explosive enemy', True), ('strong enemy', True), ('weak enemy', True), ('adjustable enemy', True)})
add_tag('nonexistant', {
    ('coin', True),
    ('euro', True),
    ('anti coin', True),
    ('adjustable coin', True),
    ('key', True),
    ('bomb', True),
    ('mega bomb', True),
    ('cheese', True),
})
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
    # ('diagonal generator', -0.5)
])

add_tag('physical', [
    ('physical generator', 'physical')
])

add_tag('wiring', [
    ('straight wire', [0, 2]),
    ('curve wire', [0, 3]),
])

add_tag('is_storage', [
    ('storage', True),
    ('maker', True),
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
    ('ghost', 'BLOCK_GENERATOR'),
    ('phantom', 'BLOCK_GENERATOR'),
    ('zombie', 'BLOCK_GENERATOR'),
])


def get_wiring(cell_name):
    return get_tag(cell_name, 'wiring')


def is_side_wire(cell_name, side):
    return side in get_wiring(cell_name)


def genzero(cell_name):
    return get_tag(cell_name, 'gen_as') == 0


def make_stored_cell_data(cell):
    props = copy.deepcopy(cell.properties)
    props.pop('RequireMouseRelease', None)

    return {
        'name': cell.name,
        'direction': cell.direction,
        'properties': props,
    }


def create_cell_from_stored_data(stored, x, y, index_position=True):
    global next_id

    if stored is None:
        return None

    next_id += 1

    props = copy.deepcopy(stored.get('properties', {}))
    props['coins'] = props.get('coins', 0)

    cell = cells_module.Cell(
        x=x,
        y=y,
        direction=stored.get('direction', 0),
        name=stored.get('name', 'push'),
        oldx=x,
        oldy=y,
        olddirection=stored.get('direction', 0),
        effects={},
        properties=props,
        storing=None,
    )

    if not register_cell(next_id, cell, index_position=index_position):
        return None

    return next_id


def remove_cell_without_animation(cell_id):
    unregister_cell(cell_id)


def enter_storage(storage_id, entering_id, direction, force, depth, data=None):
    if data is None:
        data = {}

    if storage_id not in cells or entering_id not in cells:
        return False, force

    storage = cells[storage_id]
    entering = cells[entering_id]

    old_stored = get_stored_data(storage_id)

    if old_stored is not None:
        # The Storage still occupies this coordinate. The ejected cell is
        # temporarily kept out of the position index until push_cell moves it.
        pushed_out_id = create_cell_from_stored_data(
            old_stored,
            storage.x,
            storage.y,
            index_position=False,
        )

        if pushed_out_id is None:
            return False, force

        crossed = data.get('crossed') or set()

        success, force = push_cell(
            pushed_out_id,
            direction,
            force,
            depth - 1,
            {
                'lastcell': entering_id,
                'crossed': crossed,
            }
        )

        if not success:
            remove_cell_without_animation(pushed_out_id)
            return False, force

    if entering_id not in cells:
        storage.properties['stored'] = None
        return True, force

    storage.properties['stored'] = make_stored_cell_data(entering)
    remove_cell_without_animation(entering_id)

    return True, force


images = load_all_images(resource_path('textures'))
audio = load_all_audio(resource_path('audio'))

music = audio['Load 15 cells']
music.play(loops=-1)

border_ids = {}
cells = {}
grid = {}

edit_icon = images['edit'] or images['notex']

subcategories = {
    'movers': ['mover', 'leaper', 'cw knight', 'ccw knight', 'super mover', 'adjustable mover', 'advancer', 'veerer',
               'rotator mover', 'purple mover', 'hydra', 'bird', 'bee'],
    'pullers': ['puller', 'leap puller', 'super puller', 'advancer'],
    'walls': ['wall', 'ghost', 'lock'],
    'pushables': ['push', 'slide', '3-way push', '1-way push', 'bent slide', '0-way push', 'random push', 'arrow',
                  'acid', 'balloon', 'sticky', 'hyper sticky', 'lichen'],
    'weights': ['weight', 'anti weight', 'nano weight', 'anti nano weight', 'adjustable weight', 'infinite weight',
                'infinitesimal weight', 'anti infinite weight', 'anti infinitesimal weight', 'a weight', 'gold', 'lead',
                'conductance', 'restrictor', 'compensator', 'bread', 'toast'],
    'rotators': ['cw rotator', 'cw half rotator', 'cw fast rotator', 'ccw rotator', 'ccw half rotator',
                 'ccw fast rotator', 'random rotator', 'random half rotator', 'random fast rotator', '180 rotator',
                 '0 rotator'],
    'trashes': ['trash', 'stall trash', 'explosive trash', 'phantom', 'googler'],
    'enemies': ['enemy', 'strong enemy', 'adjustable enemy', 'weak enemy', 'friend', 'explosive enemy', 'zombie'],
    'generation': ['ungeneratable', 'monogeneratable', 'semigeneratable', 'adjustable generatable', 'antigeneratable'],
    'generators': ['generator', 'cw generator', 'cw valve generator', 'ccw generator', 'ccw valve generator',
                   'bi generator', 'tri generator', 'cw skew generator', 'ccw skew generator', 'bi skew generator',
                   'tri skew generator', 'physical generator', 'single cell generator'],
    'makers': ['maker'],
    'effect givers': ['disabler', 'enabler', 'electrocutor', 'statifier'],
    'repulsors': ['repulsor', 'randulsor'],
    'impulsors': ['impulsor', 'randulsor'],
    'gears': ['cw gear', 'ccw gear', '180 gear', 'random gear', 'cw half gear', 'ccw half gear', 'random half gear',
              'cw fast gear', 'ccw fast gear', 'random fast gear', 'cw mini gear', 'ccw mini gear', '180 mini gear',
              'random mini gear', 'jam', 'jelly'],
    'mirrors': ['mirror'],
    'divergers': ['straight diverger', 'curve diverger', 'cross diverger', 'diode diverger', 'cw diode diverger',
                  'ccw diode diverger', 'curve displacer', 'cw diode displacer',
                  'ccw diode displacer', 'coin diverger',],
    'slopes': ['slope'],
    'forkers':['forker'],
    'numbers': ['number'],
    'wires': ['straight wire', 'curve wire'],
    'operations': ['add', 'subtract', 'multiply'],
    'storing': ['storage', 'self'],
    'redirectors': ['redirector'],
    'players': ['player', 'fragile player', 'platformer player', 'cube roll'],
    'flippers': ['flipper'],
    'collectables': ['coin', 'anti coin', 'adjustable coin', 'coin diverger', 'euro', 'key', 'lock', 'bomb', 'mega bomb', 'cheese'],
    'physics': ['inertia'],
    'intakers': ['intaker', 'super intaker'],
    'other': ['randomer', 'balloon', 'acid', 'lichen', 'googler'],
    'infectors': ['crimson', 'warped', 'corruption', 'fungal'],
    'other rotators': ['anchor', 'hinge'],
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
        'sub': [subcategories['movers'], subcategories['pullers'], subcategories['players']],
    },
    {
        'name': 'Rotators',
        'texture': images['cw rotator'] or images['notex'],  # fix texture name
        'sub': [subcategories['rotators'], subcategories['flippers'], subcategories['redirectors'],
                subcategories['gears'], subcategories['other rotators']],
    },
    {
        'name': 'Destroyers',
        'texture': images['trash'] or images['notex'],
        'sub': [subcategories['trashes'], subcategories['enemies'], subcategories['intakers']],
    },
    {
        'name': 'Forcers',
        'texture': images['repulsor'] or images['notex'],
        'sub': [subcategories['repulsors'], subcategories['impulsors'], subcategories['gears'],
                subcategories['mirrors']],
    },
    {
        'name': 'Recreation',
        'texture': images['generator'] or images['notex'],
        'sub': [subcategories['generators'], subcategories['makers'], subcategories['generation']],
    },
    {
        'name': 'Divergers',
        'texture': images['straight diverger'] or images['notex'],
        'sub': [subcategories['divergers'], subcategories['forkers'], subcategories['slopes']],
    },
    {
        'name': 'Math',
        'texture': images['number'] or images['notex'],
        'sub': [subcategories['numbers'], subcategories['wires'], subcategories['operations']],
    },
    {
        'name': 'Miscellaneous',
        'texture': images['disabler'] or images['notex'],
        'sub': [subcategories['effect givers'], subcategories['storing'], subcategories['players'],
                subcategories['collectables'], subcategories['physics'], subcategories['infectors'],
                subcategories['other']],
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


def draw_storage(cell, properties, alpha=255):
    stored = cell.properties.get('stored')

    if stored is None:
        return

    x = anim.lerp_position(cell.oldx, cell.x, lerp)
    y = anim.lerp_position(cell.oldy, cell.y, lerp)
    direction = stored.get('direction', 0)
    name = stored.get('name', 'push')

    size = int(image_size * zoom)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    rect = pygame.Rect(screen_x, screen_y, size, size)

    img = pygame.transform.scale(images[name] or images['notex'], (int(size / 2), int(size / 2)))
    rotated = pygame.transform.rotate(img, direction * -90)
    rotated.set_alpha(alpha)

    rotated_rect = rotated.get_rect(center=rect.center)
    screen.blit(rotated, rotated_rect)


def draw_number(cell, properties, alpha=255):
    x, y = cell.x, cell.y

    value = list(properties.values())[0]

    outlinecolor = pygame.color.Color(189, 222, 255) if cell.name == 'number' else images[cell.name].get_at((1, 7))

    text = font.render(str(value), True, (255, 255, 255))
    text = pygame.transform.scale(text, (text.get_width() * zoom / 2, text.get_height() * zoom / 2))
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

    for dx, dy in [(-zoom, -zoom), (-zoom, 0), (-zoom, zoom), (0, -zoom), (0, zoom), (zoom, -zoom), (zoom, 0),
                   (zoom, zoom)]:
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


def draw_coin_count(cell, properties, alpha=255):
    x, y = anim.lerp_position(cell.oldx, cell.x, lerp), anim.lerp_position(cell.oldy, cell.y, lerp)

    value = properties['coins']

    text = font.render(str(value), True, (255, 255, 255))
    text = pygame.transform.scale(text, (text.get_width() * zoom / 2, text.get_height() * zoom / 2))
    text.set_alpha(alpha)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    cell_size = image_size * zoom

    text_rect = text.get_rect(
        center=(
            screen_x + cell_size / 2.7 + (text.get_width() / 2),
            screen_y + cell_size / 1.2
        )
    )

    screen.blit(text, text_rect)

def draw_euro_count(cell, properties, alpha=255):
    x, y = anim.lerp_position(cell.oldx, cell.x, lerp), anim.lerp_position(cell.oldy, cell.y, lerp)

    value = properties['euros']

    text = font.render(str(value), True, (255, 255, 255))
    text = pygame.transform.scale(text, (text.get_width() * zoom / 2, text.get_height() * zoom / 2))
    text.set_alpha(alpha)

    screen_x = x * image_size * zoom + camera_pos['x']
    screen_y = y * image_size * zoom + camera_pos['y']

    cell_size = image_size * zoom

    text_rect = text.get_rect(
        center=(
            screen_x + cell_size / 2.7 + (text.get_width() / 2),
            screen_y + cell_size / 1.2 - (cell_size / 3.3)
        )
    )

    screen.blit(text, text_rect)


def draw_fraction(cell, properties, alpha=255):
    x, y = cell.x, cell.y

    value = str(list(properties.values())[0]) + '/' + str(list(properties.values())[1])

    outlinecolor = images[cell.name].get_at((1, 7))

    text = font.render(str(value), True, (255, 255, 255))
    text = pygame.transform.scale(text, (text.get_width() * zoom / 2, text.get_height() * zoom / 2))
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

    for dx, dy in [(-zoom, -zoom), (-zoom, 0), (-zoom, zoom), (0, -zoom), (0, zoom), (zoom, -zoom), (zoom, 0),
                   (zoom, zoom)]:
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
    ['googler'],
    {
        'Text': ['', 'string'],
    },
    draw_none
)

adjustable(
    ['key'],
    {
        'ID': [0, 'number'],
        'Uses': [1, 'number'],
    },
    draw_number
)

adjustable(
    ['lock'],
    {
        'ID': [0, 'number'],
        'Keys Needed': [1, 'number'],
    },
    draw_number
)

adjustable(
    subcategories['rotators'],
    {
        'Right': ['None', ['None', 'Push']],
        'Down': ['None', ['None', 'Push']],
        'Left': ['None', ['None', 'Push']],
        'Up': ['None', ['None', 'Push']]
    },
    draw_sides
)

adjustable(
    ['sticky', 'hyper sticky'],
    {
        'Right': ['None', ['None', 'Push']],
        'Down': ['None', ['None', 'Push']],
        'Left': ['None', ['None', 'Push']],
        'Up': ['None', ['None', 'Push']]
    },
    draw_sides
)

adjustable(
    ['adjustable weight', 'bread'],
    {
        'Weight': [2, 'number'],
    },
    draw_number
)

adjustable(
    ['platformer player'],
    {
        'Jump Power': [2, 'number'],
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
        'Value': [0, 'number+dot'],
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

adjustable(
    ['adjustable coin', 'coin diverger'],
    {
        'Amount': [0, 'number'],
    },
    draw_number
)

adjustable(
    ['electrocutor', 'statifier'],
    {
        'Ticks': [0, 'number'],
    },
    draw_number
)

flippairs = []


def get_flip_pairs():
    global flippairs
    for name, info in celltypes.items():
        if 'CW' in name:
            flippairs.append((name.lower(), name.replace('CW', 'CCW').lower()))
        if 'CCW' in name:
            flippairs.append((name.lower(), name.replace('CCW', 'CW').lower()))
    flippairs = dict(flippairs)


get_flip_pairs()

v_cells = ['curve diverger', 'curve wire', 'bent slide', 'curve displacer']


def flip_direction(direction, axis):
    direction %= 4
    axis %= 2

    # up/down swap, diagonals mirror vertically
    if axis == 1:
        return (-direction) % 4

    # left/right swap, diagonals mirror horizontally
    if axis == 0:
        return (2 - direction) % 4

    # diagonal axis 0.5 / 2.5
    if axis == 1.5:
        return (1 - direction) % 4

    # diagonal axis 1.5 / 3.5
    if axis == 0.5:
        return (3 - direction) % 4

    return direction


def flip_v_direction(direction, axis):
    direction %= 4
    axis %= 2

    # horizontal/vertical mirror should only toggle between 2 states
    if axis == 0:
        if direction == 0:
            return 1
        if direction == 1:
            return 0
        if direction == 2:
            return 3
        if direction == 3:
            return 2

    if axis == 1:
        if direction == 0:
            return 3
        if direction == 3:
            return 0
        if direction == 1:
            return 2
        if direction == 2:
            return 1

    return direction


def flip_cell(cell, axis):
    if cell.name in v_cells:
        cell.direction = flip_v_direction(cell.direction, axis)
        return

    if cell.name in flippairs:
        cell.name = flippairs[cell.name]

    cell.direction = flip_direction(cell.direction, axis)


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
    return grid.get((x, y))


def rebuild_grid():
    """Rebuild the position index after replacing the entire cells dict."""
    global grid
    grid = {}

    for cell_id, cell in cells.items():
        position = (cell.x, cell.y)

        if position in grid and grid[position] != cell_id:
            raise ValueError(
                f"Two cells occupy {position}: {grid[position]} and {cell_id}"
            )

        grid[position] = cell_id


def register_cell(cell_id, cell, index_position=True):
    """Add a cell and optionally register its coordinate in the grid."""
    cells[cell_id] = cell
    effects[cell_id] = cell.effects

    if not index_position:
        return True

    position = (cell.x, cell.y)
    occupant = grid.get(position)

    if occupant is not None and occupant != cell_id:
        cells.pop(cell_id, None)
        effects.pop(cell_id, None)
        return False

    grid[position] = cell_id
    return True


def unregister_cell(cell_id):
    """Remove a cell from cells, effects, and the position index."""
    cell = cells.get(cell_id)

    if cell is not None:
        position = (cell.x, cell.y)
        if grid.get(position) == cell_id:
            grid.pop(position, None)

    cells.pop(cell_id, None)
    effects.pop(cell_id, None)

def get_stored_data(cell_id):
    stored = cells[cell_id].properties.get('stored')
    if stored is None:
        return None

    stored = stored.copy()

    if stored.get('name') == 'self':
        stored['name'] = cells[cell_id].name
        stored['properties'] = cells[cell_id].properties
        stored['direction'] = cells[cell_id].direction

    return stored

def move_cell_to(cell_id, new_x, new_y):
    """Move one cell while keeping grid[(x, y)] synchronized."""
    cell = cells.get(cell_id)
    if cell is None:
        return False

    old_position = (cell.x, cell.y)
    new_position = (new_x, new_y)
    occupant = grid.get(new_position)

    if occupant is not None and occupant != cell_id:
        return False

    if grid.get(old_position) == cell_id:
        grid.pop(old_position, None)

    cell.x = new_x
    cell.y = new_y
    grid[new_position] = cell_id
    return True


def move_cells_simultaneously(movements):
    """
    Move several cells as one operation, allowing them to swap/cycle through
    positions currently occupied by other cells in the same movement batch.
    """
    filtered = []
    moving_ids = set()
    destinations = set()

    for cell_id, new_position in movements:
        if cell_id not in cells:
            continue

        new_position = tuple(new_position)

        if cell_id in moving_ids or new_position in destinations:
            return False

        moving_ids.add(cell_id)
        destinations.add(new_position)
        filtered.append((cell_id, new_position))

    for cell_id, new_position in filtered:
        occupant = grid.get(new_position)
        if occupant is not None and occupant not in moving_ids:
            return False

    for cell_id, _ in filtered:
        cell = cells[cell_id]
        old_position = (cell.x, cell.y)
        if grid.get(old_position) == cell_id:
            grid.pop(old_position, None)

    for cell_id, new_position in filtered:
        cell = cells[cell_id]
        cell.x, cell.y = new_position
        grid[new_position] = cell_id

    return True


def add_cell(cell_name, x, y, direction, oldx=None, oldy=None, olddirection=None, effectlist=None, properties=None,
             storing=None, other=None):
    global next_id

    if (x, y) in grid:
        return None

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
        storing=storing,
    )

    prop = cell.properties.copy()

    for key, default in get_default_properties(cell_name).items():
        prop.setdefault(key, default)

    prop['tickamount'] = 1

    if cell.name == 'stall trash':
        prop['wall'] = set()

    if cell.name == 'cube roll':
        prop['RollIdx'] = 0

    if cell.name == 'inertia':
        prop['force'] = {
            'bias': 0,
            'vector': [0, 0],
        }

    if get_tag(cell.name, 'is_storage'):
        prop.setdefault('stored', None)

    prop['item'] = prop.get('item', None)
    prop['coins'] = prop.get('coins', 0)
    prop['euros'] = prop.get('euros', 0)
    cell.properties = prop

    if not register_cell(next_id, cell):
        return None

    return next_id


def copy_cell(cell_id):
    global next_id

    if cell_id not in cells:
        return None

    copied = cells[cell_id].copy()
    position = (copied.x, copied.y)

    if position in grid:
        return None

    next_id += 1

    if not register_cell(next_id, copied):
        return None

    return next_id


def delete_cell(x, y=None):
    if y is None:
        cell_id = x
    else:
        cell_id = grid.get((x, y))

        if cell_id is not None and is_border(cell_id):
            return

    if cell_id is None:
        return

    unregister_cell(cell_id)


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
    fill((0, 0), (w, h), 'ghost')
    fill((1, 1), (w - 1, h - 1), None)


# Setup
grid_borders(grid_dimensions[0], grid_dimensions[1])
border_ids = set(cells.keys())
#load_every_cell()


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
        (size - shrink, size - shrink)
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
    button_list.append(buttons.Button(
        position,
        size,
        direction,
        texture,
        onclick,
        update_visual,
        name,
    ))
    button_list[-1].snap_to(position)


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


def copy_code():
    pyperclip.copy(make_save_code())


def paste_code():
    try:
        load_save_code(pyperclip.paste())
    except Exception as e:
        print("Invalid save code:", e)


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
        # Snapshot with deep-copied properties so sim mutations don't
        # corrupt the restore point (counts, stored cells, force, etc.).
        initcells = snapshot_cells(cells)

    running = not running


def rebuild_subcategory_buttons():
    global buttons, button_list

    # remove old subcategory buttons
    button_list = [b for b in button_list if b.type != 'subcategory']

    try:
        category = categories[selected_category]
    except TypeError:
        return

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
        button = button_list[-1]

        button.set_animation(
            duration=0.4,
            lerp_type="back"
        )

        button.animate_from((
            category_x + 10,
            screen.get_height() - 50
        ))


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

        button = button_list[-1]

        button.set_animation(
            duration=0.35,
            lerp_type="back"
        )

        button.animate_from((
            start_x,
            screen.get_height() - 50
        ))


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
    if selected_category == idx:
        selected_category = None
        rebuild_subcategory_buttons()
        rebuild_cell_buttons()
        return
    selected_category = idx
    selected_subcategory = None
    rebuild_subcategory_buttons()
    rebuild_cell_buttons()


def select_subcategory(idx):
    global selected_subcategory
    if selected_subcategory == idx:
        selected_subcategory = None
        rebuild_cell_buttons()
        return
    selected_subcategory = idx
    rebuild_cell_buttons()


def snapshot_cell(cell):
    """Deep-copy a cell so later mutations (properties, effects, nested state)
    cannot bleed into the saved initial state or back out of a revert."""
    snapped = cell.copy()

    # Cell.copy() is typically shallow; always isolate mutable fields.
    try:
        snapped.properties = copy.deepcopy(getattr(cell, 'properties', {}) or {})
    except Exception:
        snapped.properties = dict(getattr(cell, 'properties', {}) or {})

    try:
        snapped.effects = copy.deepcopy(getattr(cell, 'effects', {}) or {})
    except Exception:
        snapped.effects = dict(getattr(cell, 'effects', {}) or {})

    # Frozen pose for animation after revert
    snapped.oldx = snapped.x
    snapped.oldy = snapped.y
    snapped.olddirection = snapped.direction

    return snapped


def snapshot_cells(source):
    return {cell_id: snapshot_cell(cell) for cell_id, cell in source.items()}


def revert():
    global cells, grid, effects, initstate, running, lerp, eatencells, start_tick_queue, initticks, ticks

    running = False
    lerp = 0
    eatencells = {}
    start_tick_queue = []

    # Copy FROM the snapshot so the saved init state stays pristine for
    # subsequent reverts (never hand out the stored objects themselves).
    cells = snapshot_cells(initcells)
    effects = {
        cell_id: copy.deepcopy(cell.effects) if cell.effects else {}
        for cell_id, cell in cells.items()
    }
    rebuild_grid()

    initstate = True
    ticks = initticks


def set_init_state():
    global initstate, initcells, initticks, ticks
    initcells = snapshot_cells(cells)
    initticks = ticks
    initstate = True


def in_edit():
    global editing, selected_adjustable_key, dropdown_open
    global typing_number, typing_number_with_dot, typing_string, number_text
    editing = True
    dropdown_open = False
    typing_number = False
    typing_number_with_dot = False
    typing_string = False
    number_text = ""

    data = get_adjustable(selected['cell_name'].lower())
    if data:
        selected_adjustable_key = list(data.keys())[0]


def close_editor():
    global editing, dropdown_open
    global typing_number, typing_number_with_dot, typing_string, number_text
    editing = False
    dropdown_open = False
    typing_number = False
    typing_number_with_dot = False
    typing_string = False
    number_text = ""


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

    copy_rect = pygame.Rect(rect.left + 120, rect.top + 60, 75, 75)

    if copy_rect.collidepoint(pos):
        copy_code()
        audio['beep'].play()

    paste_rect = pygame.Rect(rect.left + 210, rect.top + 60, 75, 75)

    if paste_rect.collidepoint(pos):
        paste_code()
        audio['beep'].play()

    toggle_rect = pygame.Rect(rect.left + 30, rect.top + 150, 120, 40)

    if toggle_rect.collidepoint(pos):
        toggle_knights()
        return


def editor_click(pos):
    global selected_adjustable_key, dropdown_open
    global typing_number, typing_number_with_dot, typing_string, number_text

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
            typing_number = False
            typing_number_with_dot = False
            typing_string = False
            number_text = ""
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
                typing_string = False
                number_text = str(setting[0])
                return

            if setting[1] == 'number+dot':
                typing_number = False
                typing_number_with_dot = True
                typing_string = False
                number_text = str(setting[0])
                return

            if setting[1] == 'string':
                typing_number = False
                typing_number_with_dot = False
                typing_string = True
                number_text = str(setting[0]) if setting[0] is not None else ""
                return

            if setting[1] == 'bool':
                setting[0] = not setting[0]
                typing_number = False
                typing_number_with_dot = False
                typing_string = False
                dropdown_open = False
                return

            # list dropdown (e.g. side options)
            if isinstance(setting[1], list):
                dropdown_open = not dropdown_open
                typing_number = False
                typing_number_with_dot = False
                typing_string = False
                return

            return

    if dropdown_open and selected_adjustable_key is not None:
        setting = data[selected_adjustable_key]

        if isinstance(setting[1], list):
            options = setting[1]
            dropdown_rect = pygame.Rect(line_x + 30, rect.top + 60, 220, 35)
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

    copy_rect = pygame.Rect(rect.left + 120, rect.top + 30, 75, 75)

    copy_image = images['copy']

    screen.blit(
        pygame.transform.scale(copy_image, (75, 75)),
        copy_rect.topleft
    )

    paste_rect = pygame.Rect(rect.left + 210, rect.top + 30, 75, 75)

    paste_image = images['paste']

    screen.blit(
        pygame.transform.scale(paste_image, (75, 75)),
        paste_rect.topleft
    )

    x_text = font.render("Swap CW and CCW Knight textures", True, (255, 255, 255))
    x_text = pygame.transform.scale(x_text, (x_text.get_width() / 1.5, x_text.get_height() / 1.5))
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

            is_typing = typing_number or typing_number_with_dot or typing_string
            display_text = number_text if is_typing else str(current_value)

            if isinstance(setting_type, list):
                display_text += " ∨"
            elif setting_type == 'string' and not is_typing and display_text == '':
                display_text = "(empty)"

            # Highlight field while actively typing
            if is_typing:
                pygame.draw.rect(screen, (70, 110, 160), dropdown_rect, 2)

            text = small_font.render(display_text, True, (255, 255, 255))
            # Clip long strings so they don't spill past the field
            max_w = dropdown_rect.width - 16
            if text.get_width() > max_w:
                # Prefer showing the end of the string while typing
                clipped = display_text
                while clipped and small_font.size(clipped)[0] > max_w:
                    clipped = clipped[1:] if is_typing else clipped[:-1]
                if is_typing and clipped != display_text:
                    clipped = "…" + clipped
                elif not is_typing and clipped != display_text:
                    clipped = clipped + "…"
                text = small_font.render(clipped, True, (255, 255, 255))
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


add_button(images['mover'] or images['notex'], (75, 75), (10, 10), 0, toggle_running, 'Play (Space)',
           play_button_visual)
add_button(images['180 rotator'] or images['notex'], (75, 75), (10, 90), 0, revert, 'Revert')
button_list[-1].type = 'revert'
add_button(images['generator'] or images['notex'], (75, 75), (90, 90), 0, set_init_state, 'Set Initial State')
button_list[-1].type = 'revert'
add_button(edit_icon, (75, 75), (90, 10), 0, in_edit, 'Edit Cell Properties')
button_list[-1].type = 'edit'
add_button(images['menu'] or images['notex'], (75, 75), (screen.get_width() - 90, 10), 0, open_menu, 'Menu',
           update_visual=menu_visual)
button_list[-1].type = 'menu'

for i, category in enumerate(categories):
    add_button(
        category['texture'],
        (60, 60),
        (
            i * 70 + 10,
            screen.get_height() - 70
        ),
        0,
        lambda i=i: select_category(i),
        category['name'],
        category_visual
    )


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
    if button.type == 'cell' and len(desc_lines) > 0:
        max_desc_width = max(small_font.size(line)[0] for line in desc_lines)
        width = max(title_w, max_desc_width) + 10
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
        if cell.name == 'cube roll' and cell.properties['RollIdx'] > 0:
            draw_cell(
                'model (' + str(math.ceil(cell.properties['RollIdx'])) + ')',
                anim.lerp_position(cell.oldx, cell.x, lerp),
                anim.lerp_position(cell.oldy, cell.y, lerp),
                anim.lerp_position(cell.olddirection, cell.direction, lerp),
            )
            if cell.properties['RollIdx'] < 5:
                cell.properties['RollIdx'] += 0.5
            else:
                cell.properties['RollIdx'] = 0
        else:
            draw_cell(
                cell.name,
                anim.lerp_position(cell.oldx, cell.x, lerp),
                anim.lerp_position(cell.oldy, cell.y, lerp),
                anim.lerp_position(cell.olddirection, cell.direction, lerp),
            )
        if cell.properties['coins'] != 0:
            draw_cell(
                'coin icon',
                anim.lerp_position(cell.oldx, cell.x, lerp),
                anim.lerp_position(cell.oldy, cell.y, lerp),
                0,
            )
            draw_coin_count(cell, cell.properties, alpha=255)
        if cell.properties['euros'] != 0:
            draw_cell(
                'euro icon',
                anim.lerp_position(cell.oldx, cell.x, lerp),
                anim.lerp_position(cell.oldy, cell.y, lerp),
                0,
            )
            draw_euro_count(cell, cell.properties, alpha=255)
        draw_func = get_tag_raw(cell.name, 'draw_properties')

        if cell.properties['item'] is not None:
            draw_cell(
                f'{cell.properties["item"]} icon',
                anim.lerp_position(cell.oldx, cell.x, lerp),
                anim.lerp_position(cell.oldy, cell.y, lerp),
                0,
            )

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

        if get_tag(cell.name, 'is_storage') and cell.properties.get('stored') is not None: draw_storage(cell,
                                                                                                        cell.properties,
                                                                                                        255)


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
    if not surrounding: return {0: get_cell_idx_at_pos(x + dist, y), 1: get_cell_idx_at_pos(x, y + dist),
                                2: get_cell_idx_at_pos(x - dist, y), 3: get_cell_idx_at_pos(x, y - dist)}
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


def get_diagonal_ids(x, y, dist=1):
    return {
        0.5: get_cell_idx_at_pos(x + dist, y + dist),
        1.5: get_cell_idx_at_pos(x - dist, y + dist),
        2.5: get_cell_idx_at_pos(x - dist, y - dist),
        3.5: get_cell_idx_at_pos(x + dist, y - dist)
    }


def get_neighbor_ids(x, y, dist=1):
    return get_adjacent_ids(x, y, dist=dist, surrounding=False)


def get_surrounding_ids(x, y, dist=1):
    return get_adjacent_ids(x, y, dist=dist, surrounding=True)


def move_or_delete(cell_id, newpos):
    if out_of_bounds(newpos[0], newpos[1]):
        x, y = cells[cell_id].x, cells[cell_id].y
        cell_delete(cell_id, newpos[0], newpos[1])
        return True

    return move_cell_to(cell_id, newpos[0], newpos[1])


def do_anchor(idx, rot):
    if idx is None or idx not in cells:
        return False

    doubled_rotation = round(rot * 2)

    if abs(rot * 2 - doubled_rotation) > 0.000001:
        return False

    rot = doubled_rotation / 2
    structure = get_structure(idx)

    if not structure:
        return False

    anchor_x = cells[idx].x
    anchor_y = cells[idx].y

    original_states = {
        struct_id: (
            cells[struct_id].x,
            cells[struct_id].y,
            cells[struct_id].direction
        )
        for struct_id in structure
        if struct_id in cells
    }

    for struct_id in structure:
        if struct_id not in cells:
            return False

        cell = cells[struct_id]

        if struct_id != idx and is_unbreakable(
            cell.name,
            "rotate",
            0,
            struct_id
        ):
            return False

    angle = math.radians(rot * 90)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)

    movements = []
    destinations = set()

    for struct_id in structure:
        cell = cells[struct_id]

        dx = cell.x - anchor_x
        dy = cell.y - anchor_y

        rotated_dx = round(
            dx * cos_angle - dy * sin_angle
        )

        rotated_dy = round(
            dx * sin_angle + dy * cos_angle
        )

        destination = (
            anchor_x + rotated_dx,
            anchor_y + rotated_dy
        )

        if out_of_bounds(*destination):
            return False

        if destination in destinations:
            return False

        occupant = grid.get(destination)

        if occupant is not None and occupant not in structure:
            return False

        destinations.add(destination)
        movements.append((struct_id, destination))

    if not move_cells_simultaneously(movements):
        return False

    try:
        for struct_id in structure:
            if struct_id in cells:
                cells[struct_id].direction = (
                    original_states[struct_id][2] + rot
                ) % 4

    except Exception:
        for struct_id in structure:
            if struct_id not in cells:
                continue

            cell = cells[struct_id]

            if grid.get((cell.x, cell.y)) == struct_id:
                grid.pop((cell.x, cell.y), None)

        for struct_id, state in original_states.items():
            if struct_id not in cells:
                continue

            cell = cells[struct_id]
            cell.x = state[0]
            cell.y = state[1]
            cell.direction = state[2]
            grid[(cell.x, cell.y)] = struct_id

        return False

    return True


def rotate_cell_id(idx, amt, force_dir):
    if idx is not None:
        if blocks_side(cells[idx], force_dir):
            return

        if is_unbreakable(cells[idx].name, 'rotate', to_side(force_dir, cells[idx].direction), idx):
            return

        cells[idx].direction = (cells[idx].direction + amt) % 4

        if cells[idx].name == 'anchor':
            do_anchor(idx, amt)
            cells[idx].direction = (cells[idx].direction - amt) % 4

        if cells[idx].name == 'hinge':
            frontidx = get_cell_idx_at_pos(cells[idx].x+dir_to_vec2(cells[idx].direction).x, cells[idx].y+dir_to_vec2(cells[idx].direction).y)
            if frontidx is not None: do_anchor(frontidx, amt)


def redirect_cell_id(idx, face_dir, force_dir):
    if idx is not None:
        if blocks_side(cells[idx], force_dir):
            return

        if is_unbreakable(cells[idx].name, 'redirect', to_side(force_dir, cells[idx].direction), idx):
            return

        cells[idx].direction = face_dir


def give_effect(id, effect, side):
    if id is None or id not in cells or id not in effects:
        return

    if effect in effects[id].values():
        return

    if is_unbreakable(cells[id].name, effect, side, id):
        return

    if effect == 'enabled':
        take_effect(id, 'disabled', side)

    if effect == 'statified':
        take_effect(id, 'electrocuted', side)

    effects[id][len(effects[id]) + 1] = effect


def take_effect(id, effect, side):
    if id is None: return
    if is_unbreakable(cells[id].name, 'take' + effect, side, id): return
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
        return {
            'x': x,
            'y': y,
            'direction': direction,
            'rotated': False,
            'cell_rotation': 0,
            'looped': True,
        }

    x += direction.x
    y += direction.y

    idx = get_cell_idx_at_pos(x, y)

    if idx is None:
        return {
            'x': x,
            'y': y,
            'direction': direction,
            'rotated': False,
            'cell_rotation': 0,
            'looped': False,
        }

    cell = cells[idx]
    side = to_side(vec_to_dir(direction), cell.direction)

    if cell.name == 'straight diverger':
        if side % 2 == 0:
            return step_forward(x, y, direction, loopcount, startidx)

    if cell.name == 'cross diverger':
        if side % 1 == 0:
            return step_forward(x, y, direction, loopcount, startidx)

    if cell.name == 'coin diverger':
        if side % 1 == 0:
            if cells[startidx].properties['coins'] - cell.properties['Amount'] < 0:
                return {
                    'x': x,
                    'y': y,
                    'direction': direction,
                    'rotated': False,
                    'cell_rotation': 0,
                    'looped': False,
                    'blocked': True,
                }
            else:
                cells[startidx].properties['coins'] -= cell.properties['Amount']
                return step_forward(x, y, direction, loopcount, startidx)

    if cell.name == 'diode diverger':
        if side == 2:
            return step_forward(x, y, direction, loopcount, startidx)

    if cell.name == 'slope':
        result = step_forward(x, y, direction.rotate({0: 1, 0.5: 0, 1: -1, 1.5: 0}[(side+1)%2]), loopcount, startidx)
        result['rotated'] = False
        return result

    if cell.name in ('cw diode diverger', 'ccw diode diverger', 'cw diode displacer', 'ccw diode displacer'):
        if 'ccw' in cell.name:
            turn = -1
        else:
            turn = 1
        if side == 2:
            result = step_forward(x, y, direction.rotate(turn), loopcount, startidx)
            if 'displacer' not in cell.name:
                result['cell_rotation'] = result.get('cell_rotation', 0) + turn
            result['rotated'] = True
            return result

    if cell.name in ('curve diverger', 'curve displacer'):
        turn = None

        if side == 0:
            turn = -1
        elif side == 1:
            turn = 1

        if turn is not None:
            result = step_forward(
                x,
                y,
                direction.rotate(turn),
                loopcount,
                startidx,
            )

            # Both cells bend the force/movement path.
            result['rotated'] = True

            # Only a Curve Diverger rotates the transported cell itself.
            # A Curve Displacer leaves the cell's facing direction unchanged.
            if cell.name == 'curve diverger':
                result['cell_rotation'] = result.get('cell_rotation', 0) + turn

            return result

    return {
        'x': x,
        'y': y,
        'direction': direction,
        'rotated': False,
        'cell_rotation': 0,
        'looped': False,
    }

def piping_step_forward(x, y, direction, passed=None):
    if passed is None:
        passed = set()

    c = step_forward(x, y, direction)

    cx = c['x']
    cy = c['y']
    cdir = c.get('direction', direction)

    state = (cx, cy, cdir)
    if state in passed:
        return []
    passed.add(state)
    cidx = get_cell_idx_at_pos(cx, cy)
    if cidx is not None and cidx in cells:
        def add_dir(rot):
            targets.extend(
                piping_step_forward(
                    cx,
                    cy,
                    (cdir + rot) % 4,
                    passed.copy()
                )
            )
        ccell = cells[cidx]
        side = to_side(direction, cell.direction)
        if ccell.name == 'forker' and side == 2:
            targets = []
            add_dir(1)
            add_dir(-1)
            return list(dict.fromkeys(targets))
    return [(cx, cy, cdir)]


def go_through_wires(x, y, direction, visited=None):
    """Step once in direction, then follow wires until a non-wire (or empty)."""
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

        cell = cells[idx]
        wiring = get_wiring(cell.name)

        # Non-wire endpoint — do NOT add to visited (Numbers must stay readable)
        if wiring is None:
            return {'x': x, 'y': y, 'direction': dir_num}

        if idx in visited:
            return {'x': x, 'y': y, 'direction': dir_num}

        visited.add(idx)

        enter_side = to_side(dir_num, cell.direction)
        if enter_side not in wiring:
            return {'x': x, 'y': y, 'direction': dir_num}

        exits = [s for s in wiring if s != enter_side]
        if not exits:
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
    reading_dir = reading_dir % 4

    wiring = get_wiring(cell.name)

    if wiring is not None:
        enter_side = to_side(reading_dir, cell.direction)
        if enter_side not in wiring:
            return 0

        exits = [s for s in wiring if s != enter_side]
        if not exits:
            return 0

        # Leave through the OTHER side of the wire (fixes curves + inputs)
        exit_dir = (exits[0] + cell.direction) % 4
        go_through = go_through_wires(cell.x, cell.y, exit_dir, visited)

        return get_math_value(
            get_cell_idx_at_pos(go_through['x'], go_through['y']),
            go_through['direction'],
            visited,
        )

    if cell.name == 'number':
        return cell.properties.get('Value', 0)

    if cell.name in subcategories['operations']:
        # Readable only from the output (front) side
        if cell.direction != (reading_dir + 2) % 4:
            return 0

        top_dir = (cell.direction - 1) % 4
        bot_dir = (cell.direction + 1) % 4
        top_vec = dir_to_vec2(top_dir)
        bot_vec = dir_to_vec2(bot_dir)

        top_id = get_cell_idx_at_pos(cell.x + top_vec.x, cell.y + top_vec.y)
        bot_id = get_cell_idx_at_pos(cell.x + bot_vec.x, cell.y + bot_vec.y)

        topval = get_math_value(top_id, top_dir, visited.copy())
        botval = get_math_value(bot_id, bot_dir, visited.copy())

        if cell.name == 'subtract':
            return topval - botval
        if cell.name == 'multiply':
            return topval * botval
        return topval + botval

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
    return Vec2(moves[dir % 4][0], moves[dir % 4][1])


def vec_to_dir(vec):
    raw = (math.atan2(vec.y, vec.x) / (math.pi / 2)) % 4

    snapped = round(raw * 2) / 2

    if snapped == int(snapped):
        snapped = int(snapped)

    return snapped


def cell_delete(idx, trashx, trashy):
    if idx is None or idx not in cells:
        return

    cell = cells[idx]
    x, y, direction = cell.x, cell.y, cell.direction
    has_bomb = cell.properties.get('item') in ['bomb', 'mega bomb']
    has_cheese = cell.properties.get('item') == 'cheese'

    eatencell = cell.copy()
    eatencell.oldx = x
    eatencell.oldy = y
    eatencell.x = trashx
    eatencell.y = trashy

    eatencells[len(eatencells) + 1] = eatencell
    unregister_cell(idx)

    if has_cheese:
        add_cell('cheese', x, y, direction)

    if has_bomb:
        if cell.properties.get('item') == 'bomb':
            neighbors = list(get_neighbor_ids(x, y).items())
        elif cell.properties.get('item') == 'mega bomb':
            neighbors = list(get_surrounding_ids(x, y).items())

        for direction, neighbor_id in neighbors:
            if neighbor_id is None or neighbor_id not in cells:
                continue

            neighbor = cells[neighbor_id]

            if is_unbreakable(
                neighbor.name,
                'destroy',
                to_side(direction, neighbor.direction),
                neighbor_id
            ):
                continue

            if (neighbor_id == get_cell_idx_at_pos(trashx, trashy)) :
                continue

            cell_delete(neighbor_id, x, y)


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
        return move_cell_to(b_id, a_pos[0], a_pos[1])

    if a_id is not None and b_id is None:
        return move_cell_to(a_id, b_pos[0], b_pos[1])

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
    if is_unbreakable(a.name, 'swap', a_side, a_id):
        return False

    if is_unbreakable(b.name, 'swap', b_side, b_id):
        return False

    return move_cells_simultaneously([
        (a_id, b_pos),
        (b_id, a_pos),
    ])


def do_basic_gear(idx, rot, neighbors, neighbors_to_rotate=None):
    if idx not in cells:
        return

    all_gears = [item for item in subcategories['gears'] if item != 'jelly']

    x, y = cells[idx].x, cells[idx].y

    neighbors_to_rotate = (neighbors_to_rotate or neighbors)(x, y)
    neighbors = neighbors(x, y)

    jelly_positions = set()

    for k, neighbor_id in neighbors.items():
        if neighbor_id is None or neighbor_id not in cells:
            continue

        if cells[neighbor_id].name == 'jelly':
            jelly_positions.add(k)

            if k in neighbors_to_rotate:
                neighbors_to_rotate[k] = None

    for k, neighbor_id in neighbors.items():
        if neighbor_id is None or neighbor_id not in cells:
            continue

        if cells[neighbor_id].name == 'jam':
            return

        if cells[neighbor_id].name in all_gears:
            return

        if is_unbreakable(cells[neighbor_id].name, 'swap', to_side(k, cells[neighbor_id].direction),
                          cells[neighbor_id]):
            return

    movements = []

    for k, neighbor_id in neighbors.items():
        if neighbor_id is None or neighbor_id not in cells:
            continue

        if k in jelly_positions:
            continue

        newk = k

        for _ in range(len(neighbors)):
            newk = round((newk + rot) % 4, 5)

            if newk not in jelly_positions:
                break
        else:
            continue

        newvec = dir_to_vec2(newk)

        newpos = (
            x + newvec.x,
            y + newvec.y
        )

        movements.append((neighbor_id, newpos))

    if not move_cells_simultaneously(movements):
        return

    for k, neighbor_id in neighbors_to_rotate.items():
        if neighbor_id is None or neighbor_id not in cells:
            continue

        rotate_cell_id(neighbor_id, rot, k)

    rotate_cell_id(idx, rot, 0)


def do_basic_infector(idx, neighbors, infectair=False, infectwall=False, infectcell=False):
    cell = cells[idx]
    toinfect = []
    neighbors = neighbors(cell.x, cell.y)

    def cell_type(idx, side):
        d = cells[idx]
        if is_unbreakable(d.name, 'infect', side, idx):
            return 'wall'
        return 'cell'

    for k, neighbor in neighbors.items():
        if neighbor is None:
            if infectair:
                toinfect.append(k)
            continue
        neighborcell = cells[neighbor]
        if neighborcell.name == cell.name:
            continue
        if cell_type(neighbor, to_side(k, neighborcell.direction)) == 'wall':
            if infectwall:
                toinfect.append(k)
            continue
        if cell_type(neighbor, to_side(k, neighborcell.direction)) == 'cell':
            if infectcell:
                toinfect.append(k)
            continue

    for k, neighbor in neighbors.items():
        if k in toinfect:
            kvec = dir_to_vec2(k)
            cell_delete(neighbor, cell.x, cell.y)
            add_cell(cell.name, cell.x + kvec.x, cell.y + kvec.y, cell.direction, oldx=cell.x, oldy=cell.y)


def update():
    global effects, ticks, initstate, updated, start_tick_queue
    updated.clear()
    initstate = False
    cell_list = list(cells.items())

    for cell in cells.values():
        cell.properties['tickamount'] = 1

    for ticks, event in start_tick_queue:
        if ticks <= 0:
            event()
    start_tick_queue = [(ticks - 1, event) for ticks, event in start_tick_queue if ticks > 0]

    for i, cell in cell_list:
        if i not in cells:
            continue

        if cells[i].name == 'disabler':
            for k, id in get_adjacent_ids(cells[i].x, cells[i].y).items():
                if id is None or id not in cells:
                    continue
                give_effect(id, 'disabled', to_side(k, cells[id].direction))

    for i, cell in cell_list:
        if i not in cells:
            continue

        if cells[i].name == 'enabler':
            for k, id in get_adjacent_ids(cells[i].x, cells[i].y).items():
                if id is None or id not in cells:
                    continue
                give_effect(id, 'enabled', to_side(k, cells[id].direction))

    for electrocutor_id, electrocutor in cell_list:
        if electrocutor_id not in cells:
            continue

        if cells[electrocutor_id].name != 'electrocutor':
            continue

        extra_ticks = cells[electrocutor_id].properties.get('Ticks', 0)

        try:
            extra_ticks = int(extra_ticks)
        except (TypeError, ValueError):
            extra_ticks = 0

        extra_ticks = max(0, extra_ticks)
        tick_amount = 1 + extra_ticks

        for direction, target_id in get_adjacent_ids(
                cells[electrocutor_id].x,
                cells[electrocutor_id].y
        ).items():
            if target_id is None or target_id not in cells:
                continue

            cells[target_id].properties['tickamount'] = max(
                cells[target_id].properties.get('tickamount', 1),
                tick_amount
            )

            give_effect(
                target_id,
                'electrocuted',
                to_side(direction, cells[target_id].direction)
            )

    for statifier_id, statifier in cell_list:
        if statifier_id not in cells:
            continue

        if cells[statifier_id].name != 'statifier':
            continue

        div_ticks = cells[statifier_id].properties.get('Ticks', 0)

        try:
            div_ticks = int(div_ticks)
        except (TypeError, ValueError):
            div_ticks = 0

        div_ticks = max(0, div_ticks)
        tick_amount = 1 + div_ticks

        for direction, target_id in get_adjacent_ids(
                cells[statifier_id].x,
                cells[statifier_id].y
        ).items():
            if target_id is None or target_id not in cells:
                continue

            cells[target_id].properties['tickamount'] = min(
                cells[target_id].properties.get('tickamount', 1),
                1/tick_amount
            )

            give_effect(
                target_id,
                'statified',
                to_side(direction, cells[target_id].direction)
            )

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
        def run_group(group):
            for cell_id, original_cell in group:
                if cell_id not in cells:
                    continue

                if cell_id in updated:
                    continue

                tick_amount = cells[cell_id].properties.get('tickamount', 1)

                try:
                    tick_amount = float(tick_amount)
                except (TypeError, ValueError):
                    tick_amount = 1.0

                if tick_amount > 1:
                    # Electrocutor-style: multiple updates this tick
                    for _ in range(int(tick_amount)):
                        if cell_id not in cells:
                            break

                        current_cell = cells[cell_id]
                        update_func(cell_id, current_cell, current_cell.direction)
                else:
                    # Statifier-style: update every N ticks
                    # tick_amount == 1 -> every tick
                    # tick_amount == 0.5 -> every 2 ticks, etc.
                    if tick_amount <= 0:
                        period = 1
                    elif tick_amount >= 1:
                        period = 1
                    else:
                        period = max(1, int(round(1.0 / tick_amount)))

                    if ticks % period == 0:
                        if cell_id not in cells:
                            break

                        current_cell = cells[cell_id]
                        update_func(cell_id, current_cell, current_cell.direction)

                updated.add(cell_id)

        if axis == 'h':
            group = []

            for cell_id, cell in cell_list:
                if (
                        cell_id in cells
                        and cells[cell_id].name in cell_names
                        and cells[cell_id].direction in (0, 2)
                ):
                    group.append((cell_id, cells[cell_id]))

            sort_directional_cells(group, 0 if reverse else 2)
            run_group(group)
            return

        if axis == 'v':
            group = []

            for cell_id, cell in cell_list:
                if (
                        cell_id in cells
                        and cells[cell_id].name in cell_names
                        and cells[cell_id].direction in (1, 3)
                ):
                    group.append((cell_id, cells[cell_id]))

            sort_directional_cells(group, 1 if reverse else 3)
            run_group(group)
            return

        for direction in UPDATE_DIRS:
            group = []

            for cell_id, cell in cell_list:
                if (
                        cell_id in cells
                        and cells[cell_id].name in cell_names
                        and cells[cell_id].direction == direction
                ):
                    group.append((cell_id, cells[cell_id]))

            sort_directional_cells(
                group,
                direction if reverse else direction + 2
            )
            run_group(group)

    def update_mover(i, cell, direction):
        success = False

        if cell.name == 'mover':
            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]

        if cell.name == 'bird':
            if direction % 2 == 0:
                if ticks % 4 == 0:
                    success = push_cell(i, dir_to_vec2(1), 1, 999, {'lastcell': i})[0]

                if ticks % 4 == 2:
                    success = push_cell(i, dir_to_vec2(3), 1, 999, {'lastcell': i})[0]

                if ticks % 2 == 1:
                    success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
                    if not success:
                        rotate_cell_id(i, 1, 0)
            else:
                success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
                if not success:
                    rotate_cell_id(i, 1, 0)

        if cell.name == 'bee':
            if ticks % 2 == 0:
                success = push_cell(i, dir_to_vec2(cell.direction + 0.5), 1, 999, {'lastcell': i})[0]
                if not success:
                    rotate_cell_id(i, 1, 0)
            else:
                success = push_cell(i, dir_to_vec2(cell.direction - 0.5), 1, 999, {'lastcell': i})[0]
                if not success:
                    rotate_cell_id(i, 1, 0)

        if cell.name == 'hydra':
            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]

            if not success:
                old_x = cell.x
                old_y = cell.y
                old_direction = cell.direction

                cw = cell.copy()
                ccw = cell.copy()

                delete_cell(i)

                global next_id

                cw.x = old_x
                cw.y = old_y
                cw.oldx = old_x
                cw.oldy = old_y
                cw.direction = (old_direction + 1) % 4
                cw.olddirection = old_direction

                ccw.x = old_x
                ccw.y = old_y
                ccw.oldx = old_x
                ccw.oldy = old_y
                ccw.direction = (old_direction - 1) % 4
                ccw.olddirection = old_direction

                next_id += 1
                cwid = next_id
                register_cell(cwid, cw, index_position=True)

                next_id += 1
                ccwid = next_id
                register_cell(ccwid, ccw, index_position=False)

                if not push_cell(cwid, dir_to_vec2(cw.direction), 1, 999, {'lastcell': cwid})[0]:
                    delete_cell(cwid)

                if not push_cell(ccwid, dir_to_vec2(ccw.direction), 1, 999, {'lastcell': ccwid})[0]:
                    delete_cell(ccwid)

        if cell.name == 'rotator mover':
            forward = step_forward(cell.x, cell.y, dir_to_vec2(cell.direction))
            front_id = get_cell_idx_at_pos(forward['x'], forward['y'])
            backward = step_forward(cell.x, cell.y, -dir_to_vec2(cell.direction))
            back_id = get_cell_idx_at_pos(backward['x'], backward['y'])
            rotate_cell_id(front_id, 1, cell.direction)
            rotate_cell_id(back_id, -1, (cell.direction + 2) % 4)
            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]

        if cell.name == 'purple mover':
            success = push_cell(i, dir_to_vec2(cell.direction), 1, 999, {'lastcell': i})[0]
            if not success:
                cell_delete(i, cell.x, cell.y)

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
                if ticks % prop['Delay'] != 0:
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

    def update_randomer(i, cell):
        if cell.name == 'randomer':
            possible_cells = [
                name.lower()
                for name in celltypes.keys()
                if name.lower() != 'randomer'
            ]
            x, y, dir = cell.x, cell.y, cell.direction
            delete_cell(cell.x, cell.y)
            add_cell(random.choice(possible_cells), x, y, dir)

    def update_player(i, cell):
        if cell.name == 'player' or cell.name == 'fragile player' or cell.name == 'cube roll':
            keys = pygame.key.get_pressed()
            direction = Vec2(0, 0)
            if keys[pygame.K_LEFT]:
                direction = Vec2(-1, 0)
            elif keys[pygame.K_RIGHT]:
                direction = Vec2(1, 0)
            elif keys[pygame.K_UP]:
                direction = Vec2(0, -1)
            elif keys[pygame.K_DOWN]:
                direction = Vec2(0, 1)
            if push_cell(i, direction, 1, 999, {'lastcell': i})[0] and cell.name == 'cube roll' and direction != Vec2(0, 0):
                cell.properties['RollIdx'] = 1
                cell.direction = vec_to_dir(direction)
                cell.olddirection = vec_to_dir(direction)
        if cell.name == 'platformer player':
            keys = pygame.key.get_pressed()

            if cell.properties.get('velocity') is None:
                cell.properties['velocity'] = Vec2(0, 0)

            velocity = cell.properties['velocity']

            def move_player_steps(cell_id, vec):
                if cell_id not in cells:
                    return False

                steps = max(abs(vec.x), abs(vec.y))

                if steps == 0:
                    return True

                step_x = 0
                step_y = 0

                if vec.x > 0:
                    step_x = 1
                elif vec.x < 0:
                    step_x = -1

                if vec.y > 0:
                    step_y = 1
                elif vec.y < 0:
                    step_y = -1

                for _ in range(steps):
                    if cell_id not in cells:
                        return False

                    success = push_cell(
                        cell_id,
                        Vec2(step_x, step_y),
                        1,
                        999,
                        {'lastcell': cell_id}
                    )[0]

                    if not success:
                        return False

                return True

            # ground check is ALWAYS directly below the player
            on_ground = get_cell_idx_at_pos(cell.x, cell.y + 1) is not None

            # left/right movement
            horizontal = 0

            if keys[pygame.K_LEFT]:
                horizontal = -1
            elif keys[pygame.K_RIGHT]:
                horizontal = 1

            if horizontal != 0:
                move_player_steps(i, Vec2(horizontal, 0))

            if i not in cells:
                return

            # jump
            if keys[pygame.K_UP] and on_ground:
                velocity.y = -cell.properties['Jump Power'] - 1

            # gravity
            velocity.y += 1

            # vertical movement, one cell at a time so it cannot skip walls
            if velocity.y != 0:
                success = move_player_steps(i, Vec2(0, velocity.y))

                if not success:
                    velocity.y = 0

            if i in cells:
                cells[i].properties['velocity'] = velocity

    def update_gear(i, cell):
        if cell.name == 'cw gear':
            do_basic_gear(i, 1, get_surrounding_ids)
        if cell.name == 'ccw gear':
            do_basic_gear(i, -1, get_surrounding_ids)
        if cell.name == '180 gear':
            do_basic_gear(i, 2, get_surrounding_ids)
        if cell.name == 'random gear':
            do_basic_gear(i, random.choice([1, -1]), get_surrounding_ids)
        if cell.name == 'cw half gear':
            do_basic_gear(i, 0.5, get_surrounding_ids)
        if cell.name == 'ccw half gear':
            do_basic_gear(i, -0.5, get_surrounding_ids)
        if cell.name == 'random half gear':
            do_basic_gear(i, random.choice([0.5, -0.5]), get_surrounding_ids)
        if cell.name == 'cw fast gear':
            do_basic_gear(i, 1.5, get_surrounding_ids)
        if cell.name == 'ccw fast gear':
            do_basic_gear(i, -1.5, get_surrounding_ids)
        if cell.name == 'random fast gear':
            do_basic_gear(i, random.choice([1.5, -1.5]), get_surrounding_ids)
        if cell.name == 'cw mini gear':
            do_basic_gear(i, 1, get_adjacent_ids)
        if cell.name == 'ccw mini gear':
            do_basic_gear(i, -1, get_adjacent_ids)
        if cell.name == '180 mini gear':
            do_basic_gear(i, 2, get_adjacent_ids)
        if cell.name == 'random mini gear':
            do_basic_gear(i, random.choice([1, -1]), get_adjacent_ids)

    def update_puller(i, cell, direction):
        global undocells, cells, grid, effects
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
                effects = {cell_id: restored.effects for cell_id, restored in cells.items()}
                rebuild_grid()
        elif cell.name == 'diagonal puller':
            pull_cell(i, dir_to_vec2(cell.direction - 0.5), 1, 999, {'lastcell': i})
        elif cell.name == 'leap puller':
            pull_cell(i, dir_to_vec2(cell.direction).multiply(2), 1, 999, {'lastcell': i})

    def _normalize_gen_params(cell_name):
        """Shared gen_rotate / gen_move / gen_output_offset handling."""
        rotations = get_tag(cell_name, 'gen_rotate')
        if rotations is None:
            rotations = [0]
        elif isinstance(rotations, (int, float)):
            rotations = [rotations]

        move_offset = get_tag(cell_name, 'gen_move') or 0

        output_offsets = get_tag(cell_name, 'gen_output_offset')
        if output_offsets is None:
            output_offsets = [0]
        elif isinstance(output_offsets, (int, float)):
            output_offsets = [output_offsets]

        return rotations, move_offset, output_offsets

    def _resolve_genas(source_name, source_props, source_side, source_obj):
        """Resolve gen_as tag into (name_or_0, props, blocked)."""
        genas = get_tag(source_name, 'gen_as', source_obj, source_side)
        if genas is None:
            genas = source_name
        if genas == 'BLOCK_GENERATOR':
            return None, None, True
        gen_props = source_props
        if isinstance(genas, dict):
            gen_props = genas.get('properties', gen_props)
            genas = genas.get('name', source_name)
        return genas, gen_props, False

    def _emit_outputs(gen_cell_id, gen_cell, direction, genas, gen_props, behind_direction,
                      rotations, move_offset, output_offsets, single_cell=False):
        """
        Shared place/push/fork logic for generators and makers.
        behind_direction: facing of the cell being cloned.
        """
        gx, gy = gen_cell.x, gen_cell.y
        genz = genas == 0
        physical_type = get_tag(gen_cell.name, 'physical')

        for rot in rotations:
            for output_offset in output_offsets:
                out_dir = (direction + move_offset + output_offset + rot) % 4
                out_vec = dir_to_vec2(out_dir)

                forward = step_forward(gx, gy, out_vec)
                frontpos = (forward['x'], forward['y'])
                front_id = get_cell_idx_at_pos(frontpos[0], frontpos[1])

                # Prefer forking into a correctly-oriented forker over pushing it away
                if (not genz and front_id is not None and front_id in cells
                        and cells[front_id].name == 'forker'):
                    gen_dir = behind_direction + move_offset + rot
                    if try_fork_generated(front_id, genas, gen_dir, gen_props, out_vec):
                        continue

                if single_cell and front_id is not None:
                    continue

                placed_dir = behind_direction + move_offset + rot

                if front_id is None or push_cell(front_id, out_vec, 1, 999, {'lastcell': front_id})[0]:
                    if not genz:
                        add_cell(genas, frontpos[0], frontpos[1], placed_dir,
                                 gx, gy, behind_direction, properties=gen_props)
                elif physical_type == 'physical' and push_cell(
                        gen_cell_id, dir_to_vec2((direction + 2) % 4), 1, 999,
                        {'lastcell': gen_cell_id})[0]:
                    gx, gy = gen_cell.x, gen_cell.y
                    forward = step_forward(gx, gy, out_vec)
                    frontpos = (forward['x'], forward['y'])
                    if not genz:
                        add_cell(genas, frontpos[0], frontpos[1], placed_dir,
                                 gx, gy, behind_direction, properties=gen_props)

    def update_maker(i, cell, direction):
        cellbehind = get_stored_data(i)
        if cellbehind is None:
            return

        genas, gen_props, blocked = _resolve_genas(
            cellbehind['name'], cellbehind['properties'], None, cellbehind
        )
        if blocked:
            return

        rotations, move_offset, output_offsets = _normalize_gen_params(cell.name)
        _emit_outputs(
            i, cell, direction, genas, gen_props, cellbehind['direction'],
            rotations, move_offset, output_offsets,
        )

    def update_generator(i, cell, direction):
        rotations, move_offset, output_offsets = _normalize_gen_params(cell.name)
        input_dir = (direction + move_offset) % 4

        backward = step_forward(cell.x, cell.y, dir_to_vec2((input_dir + 2) % 4))
        behind_id = get_cell_idx_at_pos(backward['x'], backward['y'])
        if behind_id is None:
            return

        behindside = to_side(vec_to_dir(backward['direction']), cells[behind_id].direction)
        cellbehind = cells[behind_id].copy()

        genas, gen_props, blocked = _resolve_genas(
            cellbehind.name, cellbehind.properties, behindside, cellbehind
        )
        if blocked:
            return

        _emit_outputs(
            i, cell, direction, genas, gen_props, cellbehind.direction,
            rotations, move_offset, output_offsets,
            single_cell=(cell.name == 'single cell generator'),
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

        for cell_id, cell in cell_list:
            if cell_id in cells and cells[cell_id].name in cell_names:
                group.append((cell_id, cells[cell_id]))

        # Scan order: left-to-right, top-to-bottom.
        group.sort(key=lambda item: (item[1].y, item[1].x))

        for cell_id, original_cell in group:
            if cell_id not in cells:
                continue

            if cell_id in updated:
                continue

            tick_amount = cells[cell_id].properties.get('tickamount', 1)

            try:
                tick_amount = float(tick_amount)
            except (TypeError, ValueError):
                tick_amount = 1.0

            if tick_amount > 1:
                # Electrocutor-style: multiple updates this tick
                for _ in range(int(tick_amount)):
                    if cell_id not in cells:
                        break

                    update_func(cell_id, cells[cell_id])
            else:
                # Statifier-style: update every N ticks
                if tick_amount <= 0:
                    period = 1
                elif tick_amount >= 1:
                    period = 1
                else:
                    period = max(1, int(round(1.0 / tick_amount)))

                if ticks % period == 0:
                    if cell_id in cells:
                        update_func(cell_id, cells[cell_id])

            updated.add(cell_id)

    def update_flipper(i, cell):
        for k, id in get_adjacent_ids(cell.x, cell.y, 1).items():
            id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
            if id is None:
                continue

            if is_unbreakable(
                    cells[id].name,
                    'flip',
                    to_side(to_side(k, cells[id].direction), cells[id].direction),
                    id,
            ):
                continue

            flip_cell(cells[id], cell.direction)

    def update_infector(i, cell):
        if cell.name == 'crimson':
            do_basic_infector(i, get_neighbor_ids, infectcell=True)
        if cell.name == 'warped':
            do_basic_infector(i, get_diagonal_ids, infectcell=True)
        if cell.name == 'corruption':
            do_basic_infector(i, get_surrounding_ids, infectcell=True)

    def update_rotator(i, cell):
        amounts = {
            '0 rotator': 0,
            'cw rotator': 1,
            'ccw rotator': -1,
            '180 rotator': 2,
            'random rotator': random.randint(0, 1) * 2 - 1,
            'cw half rotator': 0.5,
            'ccw half rotator': -0.5,
            'random half rotator': (random.randint(0, 1) * 2 - 1) / 2,
            'cw fast rotator': 1.5,
            'ccw fast rotator': -1.5,
            'random fast rotator': (random.randint(0, 1) * 2 - 1) * (3 / 2),
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
            k = (k + cell.direction) % 4
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

    def update_redirector(i, cell):
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
            k = (k + cell.direction) % 4
            id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
            if id is None:
                continue

            side_index = (to_side(k, cell.direction) + 2) % 4
            side_name = sides[side_index]

            side_state = cell.properties.get(side_name, 'None')

            # if side has Push/Wall/etc, rotator does NOT work there
            if side_state != 'None':
                continue

            redirect_cell_id(id, cell.direction, k)

    def update_repulsor(i, cell):
        for k in range(0, 4):
            k = (k + cell.direction) % 4
            id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
            if id is None: continue
            push_cell(id, dir_to_vec2(k), 1, 999, {'lastcell': id})

    def update_impulsor(i, cell):
        for k in range(0, 4):
            k = (k + cell.direction) % 4
            id = get_adjacent_ids(cell.x, cell.y, 2, surrounding=True)[k]
            if id is None: continue
            pull_cell(id, dir_to_vec2((k + 2) % 4), 1, 999, {'lastcell': id})

    def update_randulsor(i, cell):
        for k in range(0, 4):
            k = (k + cell.direction) % 4
            if random.random() < .5:
                id = get_adjacent_ids(cell.x, cell.y, 2, surrounding=True)[k]
                if id is None: continue
                pull_cell(id, dir_to_vec2((k + 2) % 4), 1, 999, {'lastcell': id})
            else:
                id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
                if id is None: continue
                push_cell(id, dir_to_vec2(k), 1, 999, {'lastcell': id})

    def update_intaker(i, cell, direction):
        if cell.name == 'super intaker':
            k = cell.direction
            id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
            if id is None:
                return
            while i in cells:
                pull_cell(id, dir_to_vec2((k + 2) % 4), 1, 999, {'lastcell': id})
                k = cell.direction
                id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
                if id is None:
                    return
        k = cell.direction
        id = get_adjacent_ids(cell.x, cell.y, 1, surrounding=True)[k]
        if id is None:
            return
        pull_cell(id, dir_to_vec2((k + 2) % 4), 1, 999, {'lastcell': id})

    def update_inertia(i, cell):
        success = push_cell(i, Vec2(cell.properties['force']['vector'][0], cell.properties['force']['vector'][1]),
                            cell.properties['force']['bias'], 999, {'lastcell': i})[0]
        if not success:
            cell.properties['force']['vector'] = [0, 0]
            cell.properties['force']['bias'] = 0

    def update_math(i, cell, direction):
        # Output: follow wires in front, write into a Number if present
        front_data = go_through_wires(cell.x, cell.y, cell.direction % 4)
        frontid = get_cell_idx_at_pos(front_data['x'], front_data['y'])

        # Inputs: adjacent cells (wires are resolved inside get_math_value)
        top_dir = (cell.direction - 1) % 4
        bot_dir = (cell.direction + 1) % 4
        top_vec = dir_to_vec2(top_dir)
        bot_vec = dir_to_vec2(bot_dir)

        topid = get_cell_idx_at_pos(cell.x + top_vec.x, cell.y + top_vec.y)
        bottomid = get_cell_idx_at_pos(cell.x + bot_vec.x, cell.y + bot_vec.y)

        topval = get_math_value(topid, top_dir)
        botval = get_math_value(bottomid, bot_dir)

        if cell.name == 'add':
            answer = topval + botval
        elif cell.name == 'subtract':
            answer = topval - botval
        elif cell.name == 'multiply':
            answer = topval * botval
        else:
            return

        if frontid is not None and frontid in cells and cells[frontid].name == 'number':
            cells[frontid].properties['Value'] = answer

    run_directional_updates(cell_list, subcategories['operations'], update_math, reverse=True)
    run_directional_updates(cell_list, ['mirror'], update_mirror, 'h')
    run_directional_updates(cell_list, ['mirror'], update_mirror, 'v')
    run_directional_updates(cell_list, ['super intaker'], update_intaker)
    run_directional_updates(cell_list, ['intaker'], update_intaker)
    run_directional_updates(cell_list, subcategories['generators'], update_generator)
    run_directional_updates(cell_list, subcategories['makers'], update_maker)
    run_position_updates(cell_list, subcategories['flippers'], update_flipper)
    run_position_updates(cell_list, subcategories['rotators'], update_rotator)
    run_position_updates(cell_list, subcategories['gears'], update_gear)
    run_position_updates(cell_list, subcategories['redirectors'], update_redirector)
    run_position_updates(cell_list, ['inertia'], update_inertia)
    run_position_updates(cell_list, ['impulsor'], update_impulsor)
    run_position_updates(cell_list, ['randulsor'], update_randulsor)
    run_position_updates(cell_list, ['repulsor'], update_repulsor)
    run_directional_updates(cell_list, ['super puller'], update_puller)
    run_directional_updates(cell_list, ['puller', 'diagonal puller', 'leap puller', 'advancer'], update_puller)
    run_directional_updates(cell_list, ['super mover'], update_mover)
    run_directional_updates(cell_list,
                            ['mover', 'diagonal mover', 'leaper', 'cw knight', 'ccw knight', 'adjustable mover',
                             'veerer', 'purple mover', 'rotator mover', 'hydra', 'bird', 'bee'], update_mover)
    run_position_updates(cell_list, subcategories['players'], update_player)
    run_position_updates(cell_list, ['randomer'], update_randomer)
    run_position_updates(cell_list, subcategories['infectors'], update_infector)
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

            if cell.name == 'cube roll':
                cell.properties['RollIdx'] = 0


def same_vec(a, b):
    return a.x * b.y == a.y * b.x and (a.x * b.x + a.y * b.y) > 0


def opposite_vec(a, b):
    return a.x * b.y == a.y * b.x and (a.x * b.x + a.y * b.y) < 0


def try_fork_generated(forker_id, gen_name, gen_direction, gen_props, push_direction, force=1):
    """Try to feed a newly generated cell into a forker instead of pushing the forker.
    Returns True if the forker successfully forked the generated cell."""
    global next_id

    if forker_id not in cells:
        return False

    forker = cells[forker_id]
    input_dir = vec_to_dir(push_direction) if isinstance(push_direction, Vec2) else push_direction % 4

    if to_side(input_dir, forker.direction) != 2:
        return False

    next_id += 1
    entering_id = next_id

    props = copy.deepcopy(gen_props) if gen_props else {}
    props.setdefault('coins', 0)
    props.setdefault('euros', 0)
    props.setdefault('item', None)
    props['tickamount'] = 1

    entering = cells_module.Cell(
        x=forker.x,
        y=forker.y,
        direction=gen_direction,
        name=gen_name,
        oldx=forker.x,
        oldy=forker.y,
        olddirection=gen_direction,
        effects={},
        properties=props,
        storing=None,
    )

    if not register_cell(entering_id, entering, index_position=False):
        return False

    result = do_forker(forker_id, entering_id, push_direction, force, 999, set())

    if result is None:
        unregister_cell(entering_id)
        return False

    success, _ = result
    if not success:
        if entering_id in cells:
            unregister_cell(entering_id)
        return False

    return True


def do_forker(forker_id, entering_id, direction, force, depth, crossed):
    global next_id

    if forker_id not in cells or entering_id not in cells or depth <= 0:
        return False, force

    forker = cells[forker_id]
    input_dir = vec_to_dir(direction) if isinstance(direction, Vec2) else direction % 4

    if to_side(input_dir, forker.direction) != 2:
        return None

    if forker.properties.get('fork_tick') == ticks:
        return False, force

    forker.properties['fork_tick'] = ticks

    original = cells[entering_id].copy()
    unregister_cell(entering_id)

    succeeded = False

    for rot in (-1, 1):
        clone = original.copy()
        clone.x = forker.x
        clone.y = forker.y
        clone.oldx = original.x
        clone.oldy = original.y
        clone.direction = (original.direction + rot) % 4
        clone.olddirection = original.direction

        next_id += 1
        clone_id = next_id
        register_cell(clone_id, clone, index_position=False)

        branch_crossed = set(crossed) - {forker_id, entering_id}

        success, _ = push_cell(
            clone_id,
            dir_to_vec2((input_dir + rot) % 4),
            force,
            depth - 1,
            {
                'lastcell': clone_id,
                'crossed': branch_crossed
            }
        )

        if success:
            succeeded = True
        else:
            unregister_cell(clone_id)

    if not succeeded:
        register_cell(entering_id, original)

    return succeeded, force


def push_cell(cell_id, direction, force, depth, data=None):
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

    lastcellid = data.get('lastcell') or cell_id
    if cells.get(lastcellid) is None:
        return True, force

    if is_nonexistant(cell.name, 'push', to_side(dir_num, cell.direction), cell_id):
        if lastcellid in cells:
            if cell.name == 'coin':
                cells[lastcellid].properties['coins'] += 1

            if cell.name == 'euro':
                cells[lastcellid].properties['euros'] += 1

            if cell.name == 'anti coin':
                cells[lastcellid].properties['coins'] -= 1

            if cell.name == 'adjustable coin':
                cells[lastcellid].properties['coins'] += cell.properties['Amount']

            if cell.name == 'key':
                give_key(lastcellid, cell)

            if cell.name in ['bomb', 'mega bomb', 'cheese']:
                cells[lastcellid].properties['item'] = cell.name

        delete_cell(cell.x, cell.y)
        return True, force

    crossed = data.get('crossed') or set()

    if cell.name == 'forker' and lastcellid != cell_id:
        result = do_forker(
            cell_id,
            lastcellid,
            direction,
            force,
            depth,
            crossed
        )

        if result is not None:
            return result

    x, y = cell.x, cell.y
    forward = step_forward(x, y, direction)
    newpos = (forward['x'], forward['y'])

    if cell_id in crossed:
        return True, force

    crossed.add(cell_id)

    cell_rotation = forward.get('cell_rotation', 0)

    if forward.get('rotated', False):
        direction = forward['direction']
        dir_num = vec_to_dir(direction)

    if forward.get('blocked', False):
        return False, 0

    front_id = get_cell_idx_at_pos(newpos[0], newpos[1])
    sticky_followers = []

    if cell.name == 'lichen' and lastcellid != cell_id:
        old_x = cell.x
        old_y = cell.y
        push_dir = dir_num

        cw = cell.copy()
        ccw = cell.copy()

        delete_cell(cell_id)

        global next_id

        cw.x = old_x
        cw.y = old_y
        cw.oldx = old_x
        cw.oldy = old_y
        cw.direction = (push_dir + 1) % 4
        cw.olddirection = push_dir

        ccw.x = old_x
        ccw.y = old_y
        ccw.oldx = old_x
        ccw.oldy = old_y
        ccw.direction = (push_dir - 1) % 4
        ccw.olddirection = push_dir

        next_id += 1
        cwid = next_id
        register_cell(cwid, cw, index_position=True)

        next_id += 1
        ccwid = next_id
        register_cell(ccwid, ccw, index_position=False)

        if not push_cell(cwid, dir_to_vec2(cw.direction), force, depth - 1, {'lastcell': cwid})[0]:
            delete_cell(cwid)

        if not push_cell(ccwid, dir_to_vec2(ccw.direction), force, depth - 1, {'lastcell': ccwid})[0]:
            delete_cell(ccwid)

        return True, force

    if cell.name == 'sticky':
        sticky_followers = [
            neighbor_id
            for neighbor_id in get_neighbor_ids(x, y).values()
            if neighbor_id is not None
               and neighbor_id != front_id
               and neighbor_id != cell_id
        ]

    if cell.name == 'hyper sticky':
        sticky_followers = [
            neighbor_id
            for neighbor_id in list(get_structure(cell_id))
            if neighbor_id is not None
               and neighbor_id != front_id
               and neighbor_id != cell_id
        ]

    if cell.name == 'storage':
        return enter_storage(cell_id, lastcellid, direction, force, depth, data)

    if blocks_side(cell, dir_num):
        return False, 0

    if cell.name == 'lock':
        if try_unlock(cell_id, lastcellid):
            return True, force

        return False, 0

    if is_unbreakable(cell.name, 'push', to_side(dir_num, cell.direction), cell_id):
        return False, 0

    if cell.name in ['bread', 'toast']:
        required_bias = cell.properties.get('Weight', 2)

        if cell.name == 'toast':
            required_bias = math.sqrt(grid_dimensions[0]*grid_dimensions[1])/10

        try:
            force = force - required_bias
        except Exception:
            return False, 0

        try:
            strong_enough = force > 0
        except Exception:
            strong_enough = bool(sp.simplify(force).is_positive)

        if strong_enough:
            x = cell.x
            y = cell.y

            if lastcellid != cell_id and lastcellid in cells:
                cell_delete(lastcellid, x, y)

            cell_delete(cell_id, x, y)

            return True, force

        return False, 0

    if cells[lastcellid].name == 'acid':
        cell_delete(cell_id, cells[lastcellid].x, cells[lastcellid].y)
        cell_delete(lastcellid, cells[lastcellid].x, cells[lastcellid].y)
        return True, force

    collide_result = get_tag(cell.name, 'can_collide', cell_id, lastcellid, to_side(dir_num, cell.direction))

    if collide_result is not None and cell.name != 'fragile player' and collide_result != 'normal':
        return collide_result, force

    if data.get('nudging', False) and not get_tag(cells[front_id]):
        if front_id is not None:
            return False, 0

    if cell.name == 'resistance':
        if force != 1:
            return False, 0

    if cell.name == 'fungal':
        if not is_unbreakable(cells[lastcellid].name, 'infect', to_side(dir_num, cell.direction), lastcellid):
            cells[lastcellid].name = cell.name

    if cell.name == 'inertia':
        cell.properties['force']['bias'] = force
        cell.properties['force']['vector'] = [direction.x, direction.y]

    if cell.name == 'random push':
        if random.random() < 0.5:
            force = 0

    if cell.name == 'adjustable weight':
        force = max(force - cell.properties['Weight'], 0)

    if cell.name == 'inversion':
        push_cell(cell_id, -direction, force * 2, 999, {'crossed': {cell_id}})

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

    if cell.name == '0-way push':
        force = 0

    if cell.name == '3-way push':
        if cell.direction == (dir_num + 1) % 4:
            force = 0

    if cell.name == '1-way push':
        if cell.direction != (dir_num + 2) % 4:
            force = 0

    if cell.name == 'bent slide':
        if cell.direction == (dir_num - 1) % 4 or cell.direction == dir_num:
            force = 0

    if front_id is not None:
        front = cells[front_id]
        if front.name == 'mover' or front.name == 'hydra' or front.name == 'veerer' or front.name == 'purple mover' or front.name == 'rotator mover' or front.name == 'magenta mover' or front.name == 'bird':
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

        old_force = force

        success, new_force = push_cell(
            front_id,
            direction,
            force,
            depth - 1,
            {'lastcell': cell_id, 'crossed': crossed}
        )

        if not success:
            if cell.name == 'balloon':
                cell_delete(cell_id, cell.x, cell.y)
                return True, old_force

            return False, new_force

        force = new_force

    if force <= 0:
        return False, 0

    if cell_id not in cells:
        return True, force

    if cell_rotation:
        cells[cell_id].direction = (
                                           cells[cell_id].direction + cell_rotation
                                   ) % 4

    moved = move_or_delete(cell_id, newpos)

    if not moved:
        return False, 0

    if cell.name == 'sticky' or cell.name == 'hyper sticky' and cell_id in cells:
        for follower_id in sticky_followers:
            if follower_id not in cells:
                continue

            if follower_id in crossed:
                continue

            push_cell(
                follower_id,
                direction,
                force,
                depth - 1,
                {
                    'lastcell': cell_id,
                    'crossed': crossed,
                }
            )

    return True, force


def pull_cell(cell_id, direction, force, depth, data=None, visited=None):
    def pull_behind(x, y, direction, force, depth, cell_id):
        backward = step_forward(x, y, direction.multiply(-1))
        behindpos = (backward['x'], backward['y'])
        behind_id = get_cell_idx_at_pos(*behindpos)

        if behind_id is not None:
            pull_cell(
                behind_id,
                direction,
                force,
                depth - 1,
                {'lastcell': cell_id},
                visited
            )

    if data is None:
        data = {}

    if visited is None:
        visited = set()

    if cell_id in visited:
        return True, force

    visited.add(cell_id)

    dir_num = direction

    if isinstance(direction, Vec2):
        dir_num = vec_to_dir(direction)
    else:
        direction = dir_to_vec2(direction)

    if depth <= 0:
        return False, force

    cell = cells.get(cell_id)

    if cell is None:
        return True, force

    if is_unbreakable(
            cell.name,
            'pull',
            to_side(dir_num, cell.direction),
            cell_id
    ):
        return False, 0

    if blocks_side(cell, dir_num):
        return False, 0

    lastcellid = data.get('lastcell') or cell_id

    x, y = cell.x, cell.y

    forward = step_forward(x, y, direction)
    newpos = (forward['x'], forward['y'])

    cell_rotation = forward.get('cell_rotation', 0)

    if forward.get('rotated', False):
        direction = forward['direction']
        dir_num = vec_to_dir(direction)

    frontid = get_cell_idx_at_pos(*newpos)
    sticky_followers = {}

    if cell.name == 'sticky':
        sticky_followers = {
            neighbor_id: (
                cells[neighbor_id].x,
                cells[neighbor_id].y
            )
            for neighbor_id in get_neighbor_ids(x, y).values()
            if neighbor_id is not None
               and neighbor_id != frontid
               and neighbor_id != cell_id
               and neighbor_id in cells
        }

    elif cell.name == 'hyper sticky':
        sticky_followers = {
            follower_id: (
                cells[follower_id].x,
                cells[follower_id].y
            )
            for follower_id in get_structure(cell_id)
            if follower_id is not None
               and follower_id != frontid
               and follower_id != cell_id
               and follower_id in cells
        }

    if frontid is not None and cells[frontid].name == 'storage':
        return enter_storage(
            frontid,
            cell_id,
            direction,
            force,
            depth,
            data
        )

    if (
            frontid is not None
            and is_nonexistant(
        cells[frontid].name,
        'pull',
        to_side(dir_num, cells[frontid].direction),
        frontid
    )
    ):
        front = cells[frontid]

        if front.name == 'coin':
            cells[cell_id].properties['coins'] += 1

        if front.name == 'euro':
            cells[cell_id].properties['euros'] += 1

        if front.name == 'anti coin':
            cells[cell_id].properties['coins'] -= 1

        if front.name == 'adjustable coin':
            cells[cell_id].properties['coins'] += front.properties['Amount']

        if front.name == 'key':
            give_key(cell_id, front)

        if front.name in ['bomb', 'mega bomb', 'cheese']:
            cell.properties['item'] = front.name

        delete_cell(front.x, front.y)

    elif frontid is not None and cells[frontid].name == 'lock':
        if not try_unlock(frontid, cell_id):
            return False, 0

    elif lastcellid == cell_id and frontid is not None:
        front = cells.get(frontid)

        if front is None:
            return False, 0

        front_side = to_side(dir_num, front.direction)

        if is_unbreakable(
                front.name,
                'pull',
                front_side,
                frontid
        ):
            return False, 0

        collide_result = get_tag(
            front.name,
            'can_collide',
            frontid,
            cell_id,
            front_side
        )

        if (
                collide_result is not None
                and collide_result != 'normal'
        ):
            pull_behind(
                x,
                y,
                direction,
                force,
                depth,
                cell_id
            )

            return collide_result, force

        return False, 0

    if cell.name == 'bread':
        required_bias = cell.properties.get('Weight', 2)

        try:
            force -= required_bias
        except Exception:
            return False, 0

        try:
            strong_enough = force > 0
        except Exception:
            strong_enough = bool(
                sp.simplify(force).is_positive
            )

        if strong_enough:
            if lastcellid != cell_id and lastcellid in cells:
                cell_delete(lastcellid, cell.x, cell.y)

            cell_delete(cell_id, cell.x, cell.y)
            return True, force

        return False, 0

    collide_result = get_tag(
        cell.name,
        'can_collide',
        cell_id,
        lastcellid
    )

    if collide_result is not None:
        return collide_result, force

    if cell.name == 'random push' and random.random() < 0.5:
        force = 0

    if cell.name == 'a weight':
        force = force + 'A'

    if cell.name == 'infinite weight':
        force -= omega

    if cell.name == 'anti infinite weight':
        force += omega

    if cell.name == 'infinitesimal weight':
        force -= eps

    if cell.name == 'anti infinitesimal weight':
        force += eps

    if cell.name == 'adjustable weight':
        force = max(
            force - cell.properties['Weight'],
            0
        )

    if cell.name == 'gold' and dir_num != math.floor(dir_num):
        force = 0

    if cell.name == 'lead' and dir_num == math.floor(dir_num):
        force = 0

    if cell.name == '0-way push':
        force = 0

    if cell.name == 'weight':
        force = max(force - 1, 0)

    if cell.name == 'conductance' and force == 1:
        return False, 0

    if cell.name == 'restrictor':
        force = min(force, 1)

    if cell.name == 'compensator':
        force = max(force, 1)

    if cell.name == 'anti weight':
        force += 1

    if cell.name == 'nano weight' and lastcellid == cell_id:
        force = 0

    if cell.name == 'anti nano weight' and lastcellid != cell_id:
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
        if (
                cell.direction == (dir_num - 1) % 4
                or cell.direction == dir_num
        ):
            force = 0

    backward = step_forward(
        x,
        y,
        direction.multiply(-1)
    )

    behindpos = (
        backward['x'],
        backward['y']
    )

    behind_id = get_cell_idx_at_pos(*behindpos)
    next_pull_direction = direction

    if backward.get('rotated', False):
        next_pull_direction = backward['direction'].multiply(-1)

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
            mover_vec = dir_to_vec2(
                behind.direction - 0.5
            )

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

        if behind.name == 'leap puller':
            mover_vec = dir_to_vec2(
                behind.direction
            ).multiply(2)

            if same_vec(mover_vec, direction):
                force += 1

            if opposite_vec(mover_vec, direction):
                force -= 1

    if force <= 0:
        return False, 0

    if cell_id not in cells:
        return True, force

    old_x = cells[cell_id].x
    old_y = cells[cell_id].y
    old_direction = cells[cell_id].direction

    if cell_rotation:
        cells[cell_id].direction = (
                                           cells[cell_id].direction + cell_rotation
                                   ) % 4

    moved = move_or_delete(cell_id, newpos)

    if not moved:
        cells[cell_id].direction = old_direction
        return False, 0

    if behind_id is not None:
        result = pull_cell(
            behind_id,
            next_pull_direction,
            force,
            depth - 1,
            {'lastcell': cell_id},
            visited
        )

        if not result[0]:
            if cell_id in cells:
                move_cell_to(cell_id, old_x, old_y)
                cells[cell_id].direction = old_direction

            return False, result[1]

    if (
            cell_id in cells
            and cell.name in ('sticky', 'hyper sticky')
    ):
        crossed = set(visited)
        crossed.add(cell_id)

        for follower_id, original_position in sticky_followers.items():
            if follower_id not in cells:
                continue

            follower = cells[follower_id]

            if (
                    follower.x,
                    follower.y
            ) != original_position:
                continue

            crossed.discard(follower_id)

            push_cell(
                follower_id,
                direction,
                force,
                depth - 1,
                {
                    'lastcell': cell_id,
                    'crossed': crossed,
                }
            )

    return True, force

if __name__ == '__main__':
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
        if not mouse_buttons[0] and not mouse_buttons[2]:
            selectedlayer = None

            for cell in cells.values():
                if get_tag(cell.name, 'is_storage'):
                    cell.properties['RequireMouseRelease'] = False
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
                if typing_number or typing_number_with_dot or typing_string:
                    if event.key == pygame.K_RETURN:
                        try:
                            data = get_current_adjustable_data()
                            setting_type = data[selected_adjustable_key][1]

                            if setting_type == "number":
                                value = int(number_text)
                            elif setting_type == "number+dot":
                                value = float(number_text)
                            elif setting_type == "string":
                                value = number_text
                            else:
                                value = number_text

                            if setting_type != "string":
                                if selected_adjustable_key == 'Delay':
                                    value = max(1, value)

                                if selected_adjustable_key == 'Run':
                                    value = max(1, value)

                                if selected_adjustable_key == 'Ticks':
                                    value = max(0, value)

                            data[selected_adjustable_key][0] = value
                        except Exception:
                            pass

                        typing_number = False
                        typing_number_with_dot = False
                        typing_string = False

                    elif event.key == pygame.K_ESCAPE:
                        typing_number = False
                        typing_number_with_dot = False
                        typing_string = False
                        number_text = ""

                    elif event.key == pygame.K_BACKSPACE:
                        number_text = number_text[:-1]

                    else:
                        if typing_number:
                            keys_allowed = "-0123456789"
                        elif typing_number_with_dot:
                            keys_allowed = "-0123456789."
                        else:
                            # string: allow printable characters except control chars
                            keys_allowed = None

                        if keys_allowed is None:
                            ch = event.unicode
                            if ch and ch.isprintable() and ch not in '\r\n\t':
                                number_text += ch
                        elif event.unicode in keys_allowed:
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
                # Don't steal keys while editing a property value
                if not (typing_number or typing_number_with_dot or typing_string):
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
                idx = get_cell_idx_at_pos(place_x, place_y)

                # Decide what action this mouse hold is trying to do
                current_layer = 'place'

                if idx is not None and get_tag(cells[idx].name, 'is_storage'):
                    current_layer = 'store'

                # First valid thing you touch decides the layer for this hold
                if selectedlayer is None:
                    selectedlayer = current_layer

                # While holding, only allow the same layer
                if selectedlayer == current_layer:

                    if current_layer == 'place':
                        if idx is None:
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

                    elif current_layer == 'store':
                        storage = cells[idx]

                        # still only manually stores once per storage per hold
                        if not storage.properties.get('RequireMouseRelease', False):
                            fake_cell = cells_module.Cell(
                                name=selected.get('cell_name'),
                                x=place_x,
                                y=place_y,
                                direction=selected.get('direction'),
                                properties=get_selected_properties()
                            )

                            fake_cell.properties['coins'] = fake_cell.properties.get('coins', 0)

                            storage.properties['stored'] = make_stored_cell_data(fake_cell)
                            storage.properties['RequireMouseRelease'] = True
        if mouse_buttons[2]:
            if not editing and not menu_open and not out_of_bounds(place_x, place_y) and not clicking_button:
                idx = get_cell_idx_at_pos(place_x, place_y)

                current_layer = 'delete'

                if idx is not None and get_tag(cells[idx].name, 'is_storage') and cells[idx].properties[
                    'stored'] is not None:
                    current_layer = 'delete_storage'

                if selectedlayer is None:
                    selectedlayer = current_layer

                if selectedlayer == current_layer:
                    if current_layer == 'delete':
                        delete_cell(place_x, place_y)

                    elif current_layer == 'delete_storage':
                        storage = cells[idx]

                        if storage.properties.get('stored') is not None:
                            storage.properties['stored'] = None
        if mouse_buttons[1]:
            idx = get_cell_idx_at_pos(place_x, place_y)
            if idx is not None:
                cell = cells[idx]
                selectidx = list(celltypes.keys()).index(format_cell_name(cell.name))
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
        ticks_display = pygame.font.Font(resource_path('nokiafcellua.ttf'), 10).render(f'Ticks: {ticks}', True, (255, 255, 255))
        screen.blit(ticks_display, (10, 0))
        pygame.display.flip()
        dt_ms = clock.tick(60)
        dt = dt_ms / 1000
    pygame.quit()
