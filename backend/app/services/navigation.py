"""Pathfinding and turn-by-turn directions.

A* over the store grid, written out by hand — no external dependency, no
model call. A product's location is a fact in the database; the way there is
arithmetic. That makes it instant, free, and identical every time.
"""

import heapq
from dataclasses import dataclass

from app.store_layout import STORE_PLAN, StorePlan

Cell = tuple[int, int]

#: Average walking speed in a supermarket, metres per second.
WALK_SPEED_MS = 1.2
#: One grid cell is one metre.
METRES_PER_CELL = 1.0


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


#: One step costs this much, a turn one unit more. Because a turn is worth
#: far less than a step, the route is always a shortest one; among the
#: shortest, the one with the fewest turns wins — which reads much better as
#: directions ("straight 25 m" beats four alternating one-metre jinks).
STEP_COST = 1000
TURN_COST = 1


def find_path(start: Cell, goal: Cell, plan: StorePlan = STORE_PLAN) -> list[Cell]:
    """Shortest walkable path from start to goal, inclusive. Empty if none.

    Four-way movement with a Manhattan heuristic, which is admissible here
    (it never overestimates when diagonals are not allowed), so A* returns a
    genuinely shortest path. The search state carries the direction of travel
    so that turning can be priced.
    """
    if not plan.is_walkable(*start) or not plan.is_walkable(*goal):
        return []
    if start == goal:
        return [start]

    State = tuple[Cell, Cell]  # (cell, heading that got us there)
    start_state: State = (start, (0, 0))

    open_heap: list[tuple[int, int, State]] = [
        (manhattan(start, goal) * STEP_COST, 0, start_state)
    ]
    came_from: dict[State, State] = {}
    best_cost: dict[State, int] = {start_state: 0}
    closed: set[State] = set()

    while open_heap:
        _f, cost, state = heapq.heappop(open_heap)
        if state in closed:
            continue
        cell, heading = state

        if cell == goal:
            path = [cell]
            while state in came_from:
                state = came_from[state]
                path.append(state[0])
            return path[::-1]
        closed.add(state)

        for neighbour in plan.neighbours(*cell):
            step = (neighbour[0] - cell[0], neighbour[1] - cell[1])
            turned = heading != (0, 0) and step != heading
            tentative = cost + STEP_COST + (TURN_COST if turned else 0)
            next_state: State = (neighbour, step)
            if tentative < best_cost.get(next_state, 1 << 60):
                best_cost[next_state] = tentative
                came_from[next_state] = state
                heapq.heappush(
                    open_heap,
                    (
                        tentative + manhattan(neighbour, goal) * STEP_COST,
                        tentative,
                        next_state,
                    ),
                )

    return []


# --- Turn-by-turn directions ---------------------------------------------

#: Unit vectors and their Azerbaijani names, used for the first instruction.
#: "up" and "down" are as the shopper sees them on the map in front of them.
_HEADINGS = {
    (0, -1): "Yuxarıya",
    (0, 1): "Aşağıya",
    (-1, 0): "Sola",
    (1, 0): "Sağa",
}


def _turn(previous: Cell, nxt: Cell) -> str | None:
    """Left or right, from the cross product of the two heading vectors.

    In screen coordinates y grows downward, so a positive cross product is a
    clockwise turn — to the right.
    """
    cross = previous[0] * nxt[1] - previous[1] * nxt[0]
    if cross > 0:
        return "sağa"
    if cross < 0:
        return "sola"
    return None  # straight on, or a full reversal


def _segments(path: list[Cell]) -> list[tuple[Cell, int]]:
    """Split a path into straight runs: (direction vector, length in cells)."""
    runs: list[tuple[Cell, int]] = []
    for before, after in zip(path, path[1:]):
        step = (after[0] - before[0], after[1] - before[1])
        if runs and runs[-1][0] == step:
            runs[-1] = (step, runs[-1][1] + 1)
        else:
            runs.append((step, 1))
    return runs


def _side_of_target(final_heading: Cell, pick_point: Cell, target: Cell) -> str:
    """Is the shelf on the shopper's left or right as they arrive?"""
    to_target = (target[0] - pick_point[0], target[1] - pick_point[1])
    cross = final_heading[0] * to_target[1] - final_heading[1] * to_target[0]
    if cross > 0:
        return "sağ"
    if cross < 0:
        return "sol"
    return "qarşı"  # straight ahead — the shelf is at the end of the aisle


def build_steps(
    path: list[Cell],
    target: Cell | None = None,
    shelf_label: str | None = None,
    level: str | None = None,
) -> list[str]:
    """Human directions in Azerbaijani, one line per manoeuvre."""
    if len(path) < 2:
        return ["Siz artıq buradasınız."]

    runs = _segments(path)
    steps: list[str] = []

    first_vector, first_length = runs[0]
    heading = _HEADINGS.get(first_vector)
    steps.append(
        f"{heading} doğru {first_length} m gedin"
        if heading
        else f"Düz {first_length} m gedin"
    )

    for index in range(1, len(runs)):
        previous_vector = runs[index - 1][0]
        vector, length = runs[index]
        side = _turn(previous_vector, vector)
        if side is None:
            steps.append(f"Düz {length} m gedin")
        else:
            steps.append(f"{side.capitalize()} dönün, {length} m gedin")

    if target is not None and shelf_label:
        side = _side_of_target(runs[-1][0], path[-1], target)
        where = "qarşınızda" if side == "qarşı" else f"{side} tərəfdə"
        level_text = f", {level.lower()} rəf" if level else ""
        steps.append(f"{shelf_label}{level_text} — {where}")

    return steps


@dataclass
class Route:
    start: Cell
    goal: Cell
    path: list[Cell]
    distance_m: float
    eta_seconds: float
    steps: list[str]

    def to_dict(self) -> dict:
        return {
            "start": {"x": self.start[0], "y": self.start[1]},
            "goal": {"x": self.goal[0], "y": self.goal[1]},
            "path": [[x, y] for x, y in self.path],
            "distance_m": round(self.distance_m, 1),
            "eta_seconds": round(self.eta_seconds),
            "steps": self.steps,
        }


def route_to(
    start: Cell,
    pick_point: Cell,
    target: Cell | None = None,
    shelf_label: str | None = None,
    level: str | None = None,
    plan: StorePlan = STORE_PLAN,
) -> Route | None:
    """Walk from `start` to the aisle cell in front of a shelf."""
    path = find_path(start, pick_point, plan)
    if not path:
        return None

    distance = (len(path) - 1) * METRES_PER_CELL
    return Route(
        start=start,
        goal=pick_point,
        path=path,
        distance_m=distance,
        eta_seconds=distance / WALK_SPEED_MS,
        steps=build_steps(path, target, shelf_label, level),
    )


def walking_distance(start: Cell, goal: Cell, plan: StorePlan = STORE_PLAN) -> float:
    """Metres along the floor, or -1 when there is no route."""
    path = find_path(start, goal, plan)
    return -1.0 if not path else (len(path) - 1) * METRES_PER_CELL
