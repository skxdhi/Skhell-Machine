"""
Central mutable game state.

All simulation data lives here so the rest of the code doesn't need a sea of
module-level globals.  Existing call sites can still use the thin module-level
proxies in main.py while we migrate.
"""
from __future__ import annotations

import copy
from typing import Any, Optional

import cells as cells_module
from registry import get_tag


class GameState:
    def __init__(self, width: int = 50, height: int = 50):
        self.grid_dimensions = (width, height)
        self.cells: dict[int, cells_module.Cell] = {}
        self.grid: dict[tuple[int, int], int] = {}  # (x, y) -> cell_id
        self.effects: dict[int, dict] = {}
        self.eatencells: dict = {}
        self.undocells: dict = {}
        self.border_ids: set[int] = set()
        self.next_id = 0
        self.ticks = 0
        self.updated: set[int] = set()
        self.start_tick_queue: list = []

        # Snapshot for revert
        self.initstate = True
        self.initcells: dict = {}
        self.initticks = 0

        # Runtime flags (UI also touches these)
        self.running = False
        self.lerp = 0.0

    # ------------------------------------------------------------------
    # Bounds / borders
    # ------------------------------------------------------------------

    def out_of_bounds(self, x: int, y: int) -> bool:
        w, h = self.grid_dimensions
        return x < 0 or y < 0 or x > w or y > h

    def is_border(self, cell_id: int) -> bool:
        return cell_id in self.border_ids

    # ------------------------------------------------------------------
    # Position index
    # ------------------------------------------------------------------

    def get_cell_id_at(self, x: int, y: int) -> Optional[int]:
        return self.grid.get((x, y))

    def rebuild_grid(self) -> None:
        self.grid = {}
        for cell_id, cell in self.cells.items():
            pos = (cell.x, cell.y)
            if pos in self.grid and self.grid[pos] != cell_id:
                raise ValueError(
                    f"Two cells occupy {pos}: {self.grid[pos]} and {cell_id}"
                )
            self.grid[pos] = cell_id

    def register_cell(
        self,
        cell_id: int,
        cell: cells_module.Cell,
        index_position: bool = True,
    ) -> bool:
        self.cells[cell_id] = cell
        self.effects[cell_id] = cell.effects

        if not index_position:
            return True

        pos = (cell.x, cell.y)
        occupant = self.grid.get(pos)
        if occupant is not None and occupant != cell_id:
            self.cells.pop(cell_id, None)
            self.effects.pop(cell_id, None)
            return False

        self.grid[pos] = cell_id
        return True

    def unregister_cell(self, cell_id: int) -> None:
        cell = self.cells.get(cell_id)
        if cell is not None:
            pos = (cell.x, cell.y)
            if self.grid.get(pos) == cell_id:
                self.grid.pop(pos, None)
        self.cells.pop(cell_id, None)
        self.effects.pop(cell_id, None)

    def move_cell_to(self, cell_id: int, new_x: int, new_y: int) -> bool:
        cell = self.cells.get(cell_id)
        if cell is None:
            return False

        old_pos = (cell.x, cell.y)
        new_pos = (new_x, new_y)
        occupant = self.grid.get(new_pos)
        if occupant is not None and occupant != cell_id:
            return False

        if self.grid.get(old_pos) == cell_id:
            self.grid.pop(old_pos, None)

        cell.x = new_x
        cell.y = new_y
        self.grid[new_pos] = cell_id
        return True

    def move_cells_simultaneously(self, movements) -> bool:
        """
        Move several cells at once (allows swaps/cycles within the batch).
        movements: iterable of (cell_id, (new_x, new_y))
        """
        filtered = []
        moving_ids = set()
        destinations = set()

        for cell_id, new_position in movements:
            if cell_id not in self.cells:
                continue
            new_position = tuple(new_position)
            if cell_id in moving_ids or new_position in destinations:
                return False
            moving_ids.add(cell_id)
            destinations.add(new_position)
            filtered.append((cell_id, new_position))

        for cell_id, new_position in filtered:
            occupant = self.grid.get(new_position)
            if occupant is not None and occupant not in moving_ids:
                return False

        for cell_id, _ in filtered:
            cell = self.cells[cell_id]
            old_pos = (cell.x, cell.y)
            if self.grid.get(old_pos) == cell_id:
                self.grid.pop(old_pos, None)

        for cell_id, new_position in filtered:
            cell = self.cells[cell_id]
            cell.x, cell.y = new_position
            self.grid[new_position] = cell_id

        return True

    # ------------------------------------------------------------------
    # Create / destroy
    # ------------------------------------------------------------------

    def _alloc_id(self) -> int:
        self.next_id += 1
        return self.next_id

    def add_cell(
        self,
        cell_name: str,
        x: int,
        y: int,
        direction,
        oldx=None,
        oldy=None,
        olddirection=None,
        effectlist=None,
        properties=None,
        storing=None,
    ) -> Optional[int]:
        if (x, y) in self.grid:
            return None

        cell_id = self._alloc_id()
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
        prop['tickamount'] = 1

        if cell.name == 'stall trash':
            prop['wall'] = set()
        if cell.name == 'cube roll':
            prop['RollIdx'] = 0
        if cell.name == 'inertia':
            prop['force'] = {'bias': 0, 'vector': [0, 0]}
        if get_tag(cell.name, 'is_storage'):
            prop.setdefault('stored', None)

        prop['item'] = prop.get('item', None)
        prop['coins'] = prop.get('coins', 0)
        prop['euros'] = prop.get('euros', 0)
        cell.properties = prop

        if not self.register_cell(cell_id, cell):
            return None
        return cell_id

    def delete_cell(self, x, y=None) -> None:
        if y is None:
            cell_id = x
        else:
            cell_id = self.grid.get((x, y))
            if cell_id is not None and self.is_border(cell_id):
                return
        if cell_id is None:
            return
        self.unregister_cell(cell_id)

    def copy_cell(self, cell_id: int) -> Optional[int]:
        if cell_id not in self.cells:
            return None
        copied = self.cells[cell_id].copy()
        if (copied.x, copied.y) in self.grid:
            return None
        new_id = self._alloc_id()
        if not self.register_cell(new_id, copied):
            return None
        return new_id

    # ------------------------------------------------------------------
    # Snapshots (revert / set initial state)
    # ------------------------------------------------------------------

    @staticmethod
    def snapshot_cell(cell: cells_module.Cell) -> cells_module.Cell:
        snapped = cell.copy()
        try:
            snapped.properties = copy.deepcopy(getattr(cell, 'properties', {}) or {})
        except Exception:
            snapped.properties = dict(getattr(cell, 'properties', {}) or {})
        try:
            snapped.effects = copy.deepcopy(getattr(cell, 'effects', {}) or {})
        except Exception:
            snapped.effects = dict(getattr(cell, 'effects', {}) or {})
        snapped.oldx = snapped.x
        snapped.oldy = snapped.y
        snapped.olddirection = snapped.direction
        return snapped

    def snapshot_cells(self, source: Optional[dict] = None) -> dict:
        source = source if source is not None else self.cells
        return {cid: self.snapshot_cell(c) for cid, c in source.items()}

    def set_init_state(self) -> None:
        self.initcells = self.snapshot_cells()
        self.initticks = self.ticks
        self.initstate = True

    def revert(self) -> None:
        self.running = False
        self.lerp = 0
        self.eatencells = {}
        self.start_tick_queue = []
        self.cells = self.snapshot_cells(self.initcells)
        self.effects = {
            cid: copy.deepcopy(c.effects) if c.effects else {}
            for cid, c in self.cells.items()
        }
        self.rebuild_grid()
        self.initstate = True
        self.ticks = self.initticks

    def reset_animation_poses(self) -> None:
        """Call at the start of each visual tick so lerp starts from current pos."""
        self.eatencells = {}
        self.effects = {i: {} for i in self.cells}
        for cell in self.cells.values():
            cell.oldx = cell.x
            cell.oldy = cell.y
            cell.olddirection = cell.direction
            if cell.name == 'cube roll':
                cell.properties['RollIdx'] = 0
