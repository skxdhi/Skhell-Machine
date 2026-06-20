class Cell:
    def __init__(self, x, y, direction, name, oldx=None, oldy=None,
                 olddirection=None, effects=None, properties=None, updated=False, storing=None,
                 other=None):
        self.x = x
        self.y = y
        self.direction = direction % 4
        self.name = name.lower()

        self.oldx = oldx if oldx is not None else x
        self.oldy = oldy if oldy is not None else y
        self.olddirection = olddirection % 4 if olddirection is not None else self.direction

        self.effects = effects.copy() if effects is not None else {}
        self.properties = properties.copy() if properties is not None else {}
        self.updated = updated
        self.storing = storing

        self.other = other if other is not None else {}

    def copy(self):
        return Cell(
            self.x,
            self.y,
            self.direction,
            self.name,
            self.oldx,
            self.oldy,
            self.olddirection,
            self.effects,
            self.properties,
            self.updated,
            self.storing,
            self.other,
        )

    def reset(self):
        self.oldx = self.x
        self.oldy = self.y
        self.olddirection = self.direction
        self.effects = {}
        self.updated = False

    def pos(self):
        return (self.x, self.y)

    def set_pos(self, x, y):
        self.x = x
        self.y = y
