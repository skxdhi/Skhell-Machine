"""
Cell type registry: descriptions, tags, categories, and adjustable properties.
"""
from __future__ import annotations

import copy
import random
from typing import Any, Callable, Optional


def format_cell_name(name: str) -> str:
    words = name.split()
    new_words = []
    for w in words:
        lower = w.lower()
        if lower == "cw":
            new_words.append("CW")
        elif lower == "ccw":
            new_words.append("CCW")
        else:
            new_words.append(w.capitalize())
    return " ".join(new_words)


# ---------------------------------------------------------------------------
# Base descriptions (keys stored lowercase; display names are formatted)
# ---------------------------------------------------------------------------

CELL_DESCRIPTIONS: dict[str, str] = {
    'mover': 'Moves forward one space every tick',
    'wall': 'Stops cells that attempt to move it',
    'push': 'Can be moved by anything',
    'slide': 'Can only be pushed on the indicated sides',
    '3-way push': 'Can only be pushed on the indicated sides',
    '1-way push': 'Can only be pushed on the indicated side',
    'bent slide': 'Can only be pushed on the indicated sides',
    'cw rotator': 'Rotates adjacent cells 90 degrees clockwise',
    'ccw rotator': 'Rotates adjacent cells 90 degrees counterclockwise',
    '180 rotator': 'Rotates adjacent cells 180 degrees',
    'random rotator': 'Rotates adjacent cells 90 degrees clockwise or counterclockwise',
    'trash': 'Deletes cells that move into it',
    'enemy': 'Deletes cells that move into it and then it deletes itself',
    'generator': 'Clones the cell behind it and puts the clone in front of it',
    'disabler': 'Prevents adjacent cells from updating',
    'weight': 'Subtracts 1 unit of bias when pushed',
    'anti weight': 'Adds 1 unit of bias when pushed',
    'nano weight': 'Cannot be moved by itself, e.g. A repulsor making a cell move',
    'anti nano weight': 'Can only be moved by itself, e.g. A repulsor making a cell move',
    'repulsor': 'Pushes adjacent cells away from it',
    'enabler': 'Prevents adjacent cells from being disabled',
    'gold': 'Can only be moved orthogonally (not diagonally)',
    'lead': 'Can only be moved diagonally',
    'random push': 'Like the Push cell but it has a 1 in 2 chance to not be pushable',
    'puller': (
        'Like the Mover cell except it moves the cells behind it rather than infront, '
        'also it cant move if there is something infront of it'
    ),
    'impulsor': 'The opposite of a Repulsor, pulls cells towards it rather than pushing them away',
    'cw gear': 'Makes surrounding cells orbit around it in a clockwise motion 2x faster',
    'ccw gear': 'Makes surrounding cells orbit around it in a counterclockwise motion 2x faster',
    '180 gear': 'Makes surrounding cells orbit around it 4x faster',
    'random gear': 'Makes surrounding cells orbit around it either clockwise or counterclockwise',
    'jam': 'When a Gear tries to move it, it will stop the entire gear',
    'mirror': 'Swaps the two cells that the arrows are pointing at',
    'a weight': "Adds 'A' units of bias when pushed, I'm sure that will end well",
    'leaper': 'A Mover that has a run of 2, meaning it will jump over the cell infront of it',
    'leap puller': 'A Puller that has a run of 2, meaning it will jump over the cell infront of it',
    'ccw knight': 'A Mover with a run of 2 and a rise of 1',
    'cw knight': 'A Mover with a run of 2 and a rise of -1',
    'conductance': 'Can only be moved if the bias is not 1',
    'friend': 'Enemy but friendly, if you kill him im gonna cry',
    'advancer': 'A Puller that can move cells infront of it',
    'straight diverger': 'When a cell tries to move on one end it will be transported to the other end',
    'curve diverger': 'A Straight Diverger but an end is bent 90 degrees',
    'cw generator': (
        'A Generator but the output direction is bent 90 degrees clockwise, '
        'and the outputted cell is rotated too'
    ),
    'ccw generator': (
        'A Generator but the output direction is bent 90 degrees counterclockwise, '
        'and the outputted cell is rotated too'
    ),
    'bi generator': 'A CW Generator combined with a CCW Generator, that means it has 2 outputs',
    'tri generator': (
        "A Bi Generator combined with a normal Generator, that means it has 3 outputs.. "
        "I'm already tired of this"
    ),
    'cw valve generator': 'A CW Generator combined with a normal Generator, that means it has 2 outputs',
    'ccw valve generator': 'A CCW Generator combined with a normal Generator, that means it has 2 outputs',
    'cw skew generator': 'A Generator but its output is bent 45 degrees clockwise',
    'ccw skew generator': 'A Generator but its output is bent 45 degrees counterclockwise',
    'bi skew generator': (
        'A CW Skew Generator combined with a CCW Skew Generator, that means it has 2 outputs'
    ),
    'tri skew generator': (
        'A Bi Skew Generator combined with a normal Generator, that means it has 3 outputs... OH NOT THIS AGAI-'
    ),
    'ungeneratable': (
        'When a Generator tries to generate this cell, nothing happens, but the Generator '
        'still pushes the cell infront of it as if it did something'
    ),
    'adjustable weight': (
        'A Weight but you can change how much force it takes away, negative numbers means it adds force'
    ),
    'infinite weight': 'A Weight that takes away an infinite amount of bias when pushed',
    'anti infinite weight': 'A Weight that adds an infinite amount of bias when pushed',
    'super mover': 'A Mover that moves infinitely fast, with infinite force',
    'restrictor': 'Limits the force pushing it to 1 unit of force',
    'compensator': 'Sets the force pushing it to 1 if the amount of force is less than 1',
    'super puller': 'A Puller that moves infinitely fast, with infinite force',
    'adjustable mover': 'A Mover in which you can change its properties',
    'number': 'Stores a number, can be used to do math',
    'straight wire': 'A Wire, it can be used to connect an output to an input and vice versa',
    'curve wire': 'A Wire, it can be used to connect an output to an input and vice versa',
    'add': 'Outputs the sum of the 2 inputs',
    'monogeneratable': 'When a Generator tries to generate it, it will output Ungeneratable cells instead',
    'semigeneratable': 'Has a 1/2 chance to act like Ungeneratable',
    'adjustable generatable': (
        'When a Generator tries to generate it, it will output a copy of itself but with a count '
        'decreased by 1, if the counter is 0 it will act like Ungeneratable'
    ),
    'antigeneratable': (
        'When a Generator tries to generate it, nothing happens; think of it as disabling the generator'
    ),
    'strong enemy': 'An Enemy but it has two lives',
    'adjustable enemy': (
        'When a cell collides with it, its counter will decrease by 1, if the counter is 1 it will act like an Enemy'
    ),
    'weak enemy': 'An Enemy but it doesnt destroy the cell that collided with it, basically a reversed Trash',
    'physical generator': (
        'Like a normal Generator, but when its being blocked by something it moves itself backwards to create space'
    ),
    'cw half rotator': 'Rotates adjacent cells 45 degrees clockwise',
    'ccw half rotator': 'Rotates adjacent cells 45 degrees counterclockwise',
    'cw half gear': 'Makes surrounding cells orbit around it in a clockwise motion',
    'ccw half gear': 'Makes surrounding cells orbit around it in a counterclockwise motion',
    'random half gear': 'Makes surrounding cells orbit around either clockwise or counterclockwise',
    'random half rotator': 'Rotates adjacent cells 45 degrees clockwise or counterclockwise',
    'cw fast rotator': 'Rotates adjacent cells 135 degrees clockwise',
    'ccw fast rotator': 'Rotates adjacent cells 135 degrees counterclockwise',
    'cw fast gear': 'Makes surrounding cells orbit around it in a clockwise motion 3x faster',
    'ccw fast gear': 'Makes surrounding cells orbit around it in a counterclockwise motion 3x faster',
    'random fast rotator': 'Rotates adjacent cells 135 degrees clockwise or counterclockwise',
    'random fast gear': (
        'Makes surrounding cells orbit around it either clockwise or counterclockwise 3x faster'
    ),
    'veerer': (
        'A Mover but when it cannot move it rotates a certain amount, that amount is adjustable with '
        'multiples of 0.5, 0.5 means 45 degree rotation, it can also be negative, there is another switch for random rotation'
    ),
    'infinitesimal weight': (
        'A Weight that takes away an infinitesimal amount of bias when pushed, an infinitesimal is a '
        'number that is bigger than 0 but less that every positive real number'
    ),
    'anti infinitesimal weight': (
        'A Weight that adds an infinitesimal amount of bias when pushed, an infinitesimal is a number '
        'that is bigger than 0 but less that every positive real number'
    ),
    'subtract': 'Outputs the difference the top input and the bottom input',
    'multiply': 'Outputs the product of the 2 inputs',
    'storage': (
        'When a cell moves into it the cell thats already inside gets moved out (if there is one) and the new one comes in'
    ),
    'cross diverger': 'Like 2 perpendicular Straight Divergers layered on top of eachother',
    'ghost': 'A Wall combined with an Antigeneratable',
    'redirector': 'Rotates adjacent cells to face its direction',
    'player': 'Use arrow keys to make this cell move in that direction',
    'stall trash': (
        'Like a trash, but whenever a cell goes into it, it will then act like a wall for one tick '
        'on the side/corner the cell went in'
    ),
    'flipper': 'Flips cells horizontally, vertically, or diagonally based on what axis the flipper is facing',
    'purple mover': 'A Mover but when it cant move it gets deleted',
    'rotator mover': (
        'A Mover that rotates the cell behind it CCW and the cell in front of it CW, this looks oddly familiar...'
    ),
    'coin': 'When a cell moves into its position, the coin is deleted and that cells coin count is incremented',
    'anti coin': (
        'When a cell moves into its position, the coin is deleted and that cells coin count is decremented '
        '(the coin count can go negative)'
    ),
    'adjustable coin': 'A coin worth an adjustable amount, it can be positive or negative',
    'inertia': (
        'When the cell is pushed, it stores that force and moves with that force every tick, it does this '
        'until it hits a wall in which it loses all the momentum'
    ),
    'hydra': 'A Mover that attempts to split left and right when it hits a wall',
    'fragile player': 'A Player combined with an enemy',
    'coin diverger': (
        'A Cross Diverger that takes a specific amount of coins from whatever enters it, if the cell that '
        'crosses has insufficent balance, it acts like a wall.'
    ),
    'explosive trash': 'A Trash cell that deletes adjacent cells when something goes inside',
    'explosive enemy': 'A Enemy cell that deletes adjacent cells when it collides with something',
    'intaker': 'Like a one sided Trash that pulls cells into it on that side',
    'super intaker': 'An Intaker that can pull an entire row of cells in one tick',
    'phantom': 'A Trash that cannot be generated',
    'zombie': 'An Enemy that cannot be generated',
    'bread': 'Like An Enemy combined with an Adjustable Weight, needs a certain amount of bias to be destroyed',
    'arrow': 'A Pushable that cannot be rotated',
    'platformer player': 'A Player with gravity, like in those cool platformer games',
    'acid': 'A Pushable that deletes the cell in front of it and itself when its pushed',
    'key': (
        'A Collectable that can be put inside of locks with the same id as it, the amount of uses can also be changed'
    ),
    'lock': (
        'A Wall that can be opened by keys with the same id as it, the amount of keys it needs can also be changed'
    ),
    'balloon': 'A Pushable that gets deleted when its pressed against a wall',
    'randomer': 'Turns into a random cell',
    'randulsor': 'Randomly repulses and impulses in each direction',
    '0-way push': 'Cannot be pushed in any direction',
    'curve displacer': 'A Curve Diverger that doesnt rotate cells that come into it',
    'diode diverger': 'A Straight Diverger that only lets cells pass in one direction',
    'jelly': "Removes its position from the Gear's available neighbors",
    'electrocutor': 'Gives adjacent cells an effect that lets them update multiple times every tick',
    'sticky': 'When moved, makes its neighbors stick to it',
    'cw mini gear': 'A CW Gear that only affects adjacent cells',
    'crimson': 'Infects adjacent cells, cannot infect air',
    'warped': 'Infects diagonal cells, cannot infect air',
    'corruption': 'Infects surrounding cells, cannot infect air',
    'fungal': 'Infects cells that push it',
    'cw diode diverger': 'A Curve Diverger that only lets cells pass in one direction',
    'ccw diode diverger': 'A Curve Diverger that only lets cells pass in one direction',
    'cw diode displacer': 'A Curve Displacer that only lets cells pass in one direction',
    'ccw diode displacer': 'A Curve Displacer that only lets cells pass in one direction',
    'ccw mini gear': 'A CCW Gear that only affects adjacent cells',
    '180 mini gear': 'A 180 Gear that only affects adjacent cells',
    'random mini gear': 'A Random Gear that only affects adjacent cells',
    '0 rotator': 'Rotates adjacent cells 0 degrees, very useful for [INSERT]!',
    'hyper sticky': 'When moved, makes the entire structure stick to it',
    'anchor': 'When rotated, makes the entire structure rotate around it',
    'hinge': 'When rotated, makes the cell in front of it rotate the structure around it instead',
    'forker': (
        'Like a Diverger with 2 outputs, when a cell comes into its input, 2 are outputted on the indicated sides'
    ),
    'bomb': 'When the cell that collected it dies, it destorys adjacent cells too',
    'single cell generator': (
        'A Generator that cannot generate if there is already a cell in front of it '
        'https://www.youtube.com/@SingleCellGenerator'
    ),
    'slope': 'A Bidiverger that doesnt rotate cells or forces that go through it',
    'mega bomb': 'Bomb that destroys surrounding cells',
    'cheese': 'When the cell that collected it dies, it drops this item',
    'toast': 'Like a Bread cell but the weight is sqrt(w*h)/10) where w and h are the dimensions of the grid',
    'euro': 'A Coin worth 1.15x a normal one',
    'lichen': 'When a cell pushes it, the lichen will split like a Hydra in that direction',
    'statifier': 'The opposite of electrocutor; Adjacent cells update on the Nth tick, where N is adjustable',
    'cube roll': (
        'A Player but its cube roll, cube roll is a game by my friend '
        '[if ur seeing this his game didnt come out yet]'
    ),
    'bird': (
        'Moves in a zig zag pattern (down, forward, up, forward) it moves normally if its facing up or down though. '
        'If it fails to move forward it rotates clockwise'
    ),
    'bee': 'A Bird that takes diagonal shortcuts (down-forward, up-forward). It acts normally in all directions',
    'maker': 'A Generator that generates the stored cell inside of it',
    'self': 'When its stored the parent cell sees it as a copy of itself',
    'googler': (
        'It googles whatever value you put in when a cell goes inside '
        '(i recommend you dont trust every Googler you see)'
    ),
}


# celltypes keyed by formatted display name -> {'desc': ...} plus optional tags
celltypes: dict[str, dict[str, Any]] = {
    format_cell_name(name): {'desc': desc}
    for name, desc in CELL_DESCRIPTIONS.items()
}

cell_to_id: dict[str, int] = {}
id_to_cell: dict[int, str] = {}

for i, name in enumerate(sorted(CELL_DESCRIPTIONS.keys())):
    lower = name.lower()
    cell_to_id[lower] = i
    id_to_cell[i] = lower


# ---------------------------------------------------------------------------
# Tag system
# ---------------------------------------------------------------------------

def add_tag(tag_name: str, pairs) -> None:
    """pairs: iterable of (cell_name, value) or a dict {cell_name: value}."""
    if isinstance(pairs, dict):
        items = pairs.items()
    else:
        items = pairs
    for pair in items:
        cell_name = format_cell_name(pair[0])
        celltypes[cell_name][tag_name] = pair[1]


def get_tag(cell_name: str, key: str, *args):
    cell_name = format_cell_name(cell_name)
    if cell_name not in celltypes:
        return None
    value = celltypes[cell_name].get(key, None)
    if callable(value):
        return value(*args)
    return value


def get_tag_raw(cell_name: str, key: str):
    cell_name = format_cell_name(cell_name)
    if cell_name in celltypes:
        return celltypes[cell_name].get(key, None)
    return None


def adjustable(cell_names, inputs, draw_func=None) -> None:
    for cell_name in cell_names:
        add_tag('adjustable', [(cell_name, inputs)])
        add_tag('draw_properties', [(cell_name, draw_func)])


def get_adjustable(cell_name: str):
    return get_tag(cell_name, 'adjustable')


# ---------------------------------------------------------------------------
# Categories (for the palette UI)
# ---------------------------------------------------------------------------

SUBCATEGORIES: dict[str, list[str]] = {
    'movers': [
        'mover', 'leaper', 'cw knight', 'ccw knight', 'super mover', 'adjustable mover',
        'advancer', 'veerer', 'rotator mover', 'purple mover', 'hydra', 'bird', 'bee',
    ],
    'pullers': ['puller', 'leap puller', 'super puller', 'advancer'],
    'walls': ['wall', 'ghost', 'lock'],
    'pushables': [
        'push', 'slide', '3-way push', '1-way push', 'bent slide', '0-way push',
        'random push', 'arrow', 'acid', 'balloon', 'sticky', 'hyper sticky', 'lichen',
    ],
    'weights': [
        'weight', 'anti weight', 'nano weight', 'anti nano weight', 'adjustable weight',
        'infinite weight', 'infinitesimal weight', 'anti infinite weight',
        'anti infinitesimal weight', 'a weight', 'gold', 'lead', 'conductance',
        'restrictor', 'compensator', 'bread', 'toast',
    ],
    'rotators': [
        'cw rotator', 'cw half rotator', 'cw fast rotator', 'ccw rotator',
        'ccw half rotator', 'ccw fast rotator', 'random rotator', 'random half rotator',
        'random fast rotator', '180 rotator', '0 rotator',
    ],
    'trashes': ['trash', 'stall trash', 'explosive trash', 'phantom', 'googler'],
    'enemies': [
        'enemy', 'strong enemy', 'adjustable enemy', 'weak enemy', 'friend',
        'explosive enemy', 'zombie',
    ],
    'generation': [
        'ungeneratable', 'monogeneratable', 'semigeneratable',
        'adjustable generatable', 'antigeneratable',
    ],
    'generators': [
        'generator', 'cw generator', 'cw valve generator', 'ccw generator',
        'ccw valve generator', 'bi generator', 'tri generator', 'cw skew generator',
        'ccw skew generator', 'bi skew generator', 'tri skew generator',
        'physical generator', 'single cell generator',
    ],
    'makers': ['maker'],
    'effect givers': ['disabler', 'enabler', 'electrocutor', 'statifier'],
    'repulsors': ['repulsor', 'randulsor'],
    'impulsors': ['impulsor', 'randulsor'],
    'gears': [
        'cw gear', 'ccw gear', '180 gear', 'random gear', 'cw half gear', 'ccw half gear',
        'random half gear', 'cw fast gear', 'ccw fast gear', 'random fast gear',
        'cw mini gear', 'ccw mini gear', '180 mini gear', 'random mini gear', 'jam', 'jelly',
    ],
    'mirrors': ['mirror'],
    'divergers': [
        'straight diverger', 'curve diverger', 'cross diverger', 'diode diverger',
        'cw diode diverger', 'ccw diode diverger', 'curve displacer', 'cw diode displacer',
        'ccw diode displacer', 'coin diverger',
    ],
    'slopes': ['slope'],
    'forkers': ['forker'],
    'numbers': ['number'],
    'wires': ['straight wire', 'curve wire'],
    'operations': ['add', 'subtract', 'multiply'],
    'storing': ['storage', 'self'],
    'redirectors': ['redirector'],
    'players': ['player', 'fragile player', 'platformer player', 'cube roll'],
    'flippers': ['flipper'],
    'collectables': [
        'coin', 'anti coin', 'adjustable coin', 'coin diverger', 'euro',
        'key', 'lock', 'bomb', 'mega bomb', 'cheese',
    ],
    'physics': ['inertia'],
    'intakers': ['intaker', 'super intaker'],
    'other': ['randomer', 'balloon', 'acid', 'lichen', 'googler'],
    'infectors': ['crimson', 'warped', 'corruption', 'fungal'],
    'other rotators': ['anchor', 'hinge'],
}

# Aliases used by the rest of the game
subcategories = SUBCATEGORIES
