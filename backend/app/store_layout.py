"""The store floor plan — the single source of truth for the map.

The plan is drawn as ASCII art below. One character is one square metre.
To re-draw the store for a different shop, edit `LAYOUT` and `ZONES`; nothing
else needs to change. Everything downstream (the map API, pathfinding, where
products sit, the admin heat map) is derived from this file.

Symbols:
    #   wall
    .   aisle — walkable
    @   entrance — walkable
    $   checkout — walkable
    A-Z shelf cell belonging to that zone — NOT walkable

Rules the parser enforces (and tests check):
    * every shelf cell touches at least one walkable cell, otherwise nobody
      could ever reach the product on it;
    * the entrance and every checkout are walkable.
"""

from dataclasses import dataclass, field

# 30 columns x 18 rows, sized so that every shelf cell touches an aisle:
#   * perimeter shelves are one cell deep against the wall;
#   * the six middle gondolas are two cells wide (back-to-back shelving), so
#     each column faces its own aisle;
#   * aisles between gondolas are two metres wide.
# Perimeter is fresh food: fruit & veg, bakery and dairy along the top, meat
# down the left wall and dairy down the right. Two-metre walkways run across
# the top and bottom of the gondola block. Entrance bottom-left, tills bottom.
LAYOUT = """\
##############################
#AAAAAAAAABBBBBBBBBBCCCCCCCCC#
#............................#
#............................#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#D..FF..GG..HH..II..JJ..KK..C#
#............................#
#............................#
#............................#
#@........$...$...$..........#
##############################
"""

#: Zone code -> display name and colour. Codes must match the letters above.
ZONES: dict[str, dict] = {
    "A": {"name": "Meyvə-Tərəvəz", "color": "#22c55e"},
    "B": {"name": "Çörək və Unlu məmulatlar", "color": "#d97706"},
    "C": {"name": "Süd məhsulları", "color": "#3b82f6"},
    "D": {"name": "Ət və Toyuq", "color": "#ef4444"},
    "F": {"name": "Bakaleya", "color": "#a16207"},
    "G": {"name": "Çay-Qəhvə", "color": "#78350f"},
    "H": {"name": "İçkilər", "color": "#06b6d4"},
    "I": {"name": "Şirniyyat və Qəlyanaltı", "color": "#ec4899"},
    "J": {"name": "Təmizlik və Gigiyena", "color": "#8b5cf6"},
    "K": {"name": "Uşaq məhsulları", "color": "#f59e0b"},
}

#: Non-shelf zones, kept out of ZONES so they never receive products.
ENTRANCE_ZONE = {"code": "@", "name": "Giriş", "color": "#94a3b8"}
CHECKOUT_ZONE = {"code": "$", "name": "Kassa", "color": "#16a34a"}

WALL = "#"
AISLE = "."
ENTRANCE = "@"
CHECKOUT = "$"

Cell = tuple[int, int]


@dataclass
class Shelf:
    """One run of touching shelf cells, e.g. "Rəf 7" in the dairy zone."""

    id: int
    label: str
    zone_code: str
    zone_name: str
    cells: list[Cell]

    @property
    def bounds(self) -> dict:
        xs = [x for x, _ in self.cells]
        ys = [y for _, y in self.cells]
        return {
            "x": min(xs),
            "y": min(ys),
            "w": max(xs) - min(xs) + 1,
            "h": max(ys) - min(ys) + 1,
        }


@dataclass
class StorePlan:
    width: int
    height: int
    grid: list[str]
    walkable: list[list[bool]]
    shelves: list[Shelf]
    entrance: Cell
    checkouts: list[Cell] = field(default_factory=list)
    #: (x, y) -> shelf id, for "which shelf is this cell part of?"
    shelf_at: dict[Cell, int] = field(default_factory=dict)

    def is_inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.is_inside(x, y) and self.walkable[y][x]

    def neighbours(self, x: int, y: int) -> list[Cell]:
        """Four-way neighbours; the store has no diagonal movement."""
        return [
            (nx, ny)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if self.is_walkable(nx, ny)
        ]

    def shelf_by_id(self, shelf_id: int) -> Shelf | None:
        for shelf in self.shelves:
            if shelf.id == shelf_id:
                return shelf
        return None

    def zone_of(self, x: int, y: int) -> str | None:
        """Zone code for a shelf cell, or None for aisles and walls."""
        shelf_id = self.shelf_at.get((x, y))
        shelf = self.shelf_by_id(shelf_id) if shelf_id is not None else None
        return shelf.zone_code if shelf else None

    def pick_points(self, x: int, y: int) -> list[Cell]:
        """Walkable cells touching a shelf cell — where a shopper stands."""
        return [
            (nx, ny)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if self.is_walkable(nx, ny)
        ]


def _flood_shelf(
    grid: list[str], start: Cell, code: str, seen: set[Cell]
) -> list[Cell]:
    """Collect one connected run of same-zone shelf cells (4-way)."""
    stack = [start]
    cells: list[Cell] = []
    height = len(grid)
    width = len(grid[0])
    while stack:
        x, y = stack.pop()
        if (x, y) in seen:
            continue
        if not (0 <= x < width and 0 <= y < height):
            continue
        if grid[y][x] != code:
            continue
        seen.add((x, y))
        cells.append((x, y))
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return cells


def parse_layout(layout: str = LAYOUT) -> StorePlan:
    """Turn the ASCII art into a structure the rest of the app can use."""
    grid = [line for line in layout.splitlines() if line.strip()]
    if not grid:
        raise ValueError("Store layout is empty")

    width = max(len(line) for line in grid)
    grid = [line.ljust(width, WALL) for line in grid]
    height = len(grid)

    walkable = [
        [grid[y][x] in (AISLE, ENTRANCE, CHECKOUT) for x in range(width)]
        for y in range(height)
    ]

    entrance: Cell | None = None
    checkouts: list[Cell] = []
    for y in range(height):
        for x in range(width):
            if grid[y][x] == ENTRANCE:
                entrance = (x, y)
            elif grid[y][x] == CHECKOUT:
                checkouts.append((x, y))
    if entrance is None:
        raise ValueError("Store layout has no entrance ('@')")
    if not checkouts:
        raise ValueError("Store layout has no checkout ('$')")

    # Shelf blocks, numbered top to bottom then left to right.
    seen: set[Cell] = set()
    blocks: list[tuple[Cell, str, list[Cell]]] = []
    for y in range(height):
        for x in range(width):
            code = grid[y][x]
            if code not in ZONES or (x, y) in seen:
                continue
            cells = _flood_shelf(grid, (x, y), code, seen)
            top_left = (min(c[1] for c in cells), min(c[0] for c in cells))
            blocks.append((top_left, code, cells))

    blocks.sort(key=lambda block: block[0])
    shelves: list[Shelf] = []
    shelf_at: dict[Cell, int] = {}
    for index, (_key, code, cells) in enumerate(blocks, start=1):
        shelf = Shelf(
            id=index,
            label=f"Rəf {index}",
            zone_code=code,
            zone_name=ZONES[code]["name"],
            cells=sorted(cells, key=lambda cell: (cell[1], cell[0])),
        )
        shelves.append(shelf)
        for cell in cells:
            shelf_at[cell] = index

    return StorePlan(
        width=width,
        height=height,
        grid=grid,
        walkable=walkable,
        shelves=shelves,
        entrance=entrance,
        checkouts=checkouts,
        shelf_at=shelf_at,
    )


def plan_to_dict(plan: StorePlan) -> dict:
    """The shape `GET /api/map` returns; the frontend draws from this."""
    return {
        "width": plan.width,
        "height": plan.height,
        "rows": plan.grid,
        "walkable": plan.walkable,
        "entrance": {"x": plan.entrance[0], "y": plan.entrance[1]},
        "checkouts": [{"x": x, "y": y} for x, y in plan.checkouts],
        "zones": [
            {"code": code, "name": data["name"], "color": data["color"]}
            for code, data in ZONES.items()
        ],
        "shelves": [
            {
                "id": shelf.id,
                "label": shelf.label,
                "zone_code": shelf.zone_code,
                "zone_name": shelf.zone_name,
                "color": ZONES[shelf.zone_code]["color"],
                "cells": [{"x": x, "y": y} for x, y in shelf.cells],
                **shelf.bounds,
            }
            for shelf in plan.shelves
        ],
    }


#: Parsed once at import; the layout never changes at runtime.
STORE_PLAN = parse_layout()
