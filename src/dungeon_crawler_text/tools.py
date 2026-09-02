"""Tools for Historian and Cartographer agents to interact with persistent world state."""

from __future__ import annotations

import heapq
import json
import math
import random
from typing import Any, Optional

from dungeon_crawler_text.world_state import (
    GRID_HEIGHT,
    GRID_WIDTH,
    LEGEND,
    VALID_SYMBOLS,
    WorldStateManager,
    parse_grid_text,
    render_ascii_map,
)


TERRAIN_COSTS: dict[str, float] = {
    ".": 1.0,   # Plains
    ";": 1.0,   # Coast
    ":": 1.0,   # Farmland
    "+": 0.5,   # Existing Road
    "=": 0.5,   # Existing Bridge
    "o": 1.0,   # Outpost
    "O": 1.0,   # City
    "!": 1.0,   # Ruin
    "*": 2.5,   # Wastelands
    ",": 3.0,   # Hills
    "#": 4.0,   # Forest
    "%": 6.0,   # Swamp
    "~": 6.0,   # Water (bridge required)
    "&": 10.0,  # Dense Forest
    "/": 15.0,  # Cliffs
    "^": float("inf"),  # Impassable mountains
}


def find_path_astar(
    grid: list[list[str]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> Optional[list[tuple[int, int]]]:
    """Finds an optimal path from start to goal using A* with terrain weighting.

    Avoids mountain peaks and prefers existing roads, plains, and coasts.
    """
    sx, sy = start
    gx, gy = goal

    if not (0 <= sx < GRID_WIDTH and 0 <= sy < GRID_HEIGHT):
        return None
    if not (0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT):
        return None

    # Neighbors: 8-directional
    directions = [
        (0, 1, 1.0),
        (0, -1, 1.0),
        (1, 0, 1.0),
        (-1, 0, 1.0),
        (1, 1, 1.414),
        (-1, 1, 1.414),
        (1, -1, 1.414),
        (-1, -1, 1.414),
    ]

    def heuristic(x: int, y: int) -> float:
        return math.hypot(gx - x, gy - y)

    open_set: list[tuple[float, float, int, int]] = []
    heapq.heappush(open_set, (heuristic(sx, sy), 0.0, sx, sy))

    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    cost_so_far: dict[tuple[int, int], float] = {(sx, sy): 0.0}

    while open_set:
        _, current_cost, cx, cy = heapq.heappop(open_set)

        if (cx, cy) == (gx, gy):
            # Reconstruct path
            path: list[tuple[int, int]] = []
            curr = (cx, cy)
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.append((sx, sy))
            path.reverse()
            return path

        for dx, dy, dist_factor in directions:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                continue

            symbol = grid[ny][nx]
            base_cost = TERRAIN_COSTS.get(symbol, 2.0)
            if math.isinf(base_cost):
                continue

            # Slight jitter for organic meander
            jitter = 1.0 + (random.uniform(-0.05, 0.05))
            move_cost = base_cost * dist_factor * jitter
            new_cost = current_cost + move_cost

            if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                cost_so_far[(nx, ny)] = new_cost
                priority = new_cost + heuristic(nx, ny)
                heapq.heappush(open_set, (priority, new_cost, nx, ny))
                came_from[(nx, ny)] = (cx, cy)

    return None


class HistorianTools:
    """Tools available to the Historian agent for reading and inspecting world state."""

    def __init__(self, manager: WorldStateManager) -> None:
        self.manager = manager

    def get_world_overview(self) -> str:
        """Returns an overview of the latest world state including current epoch, realm name,

        counts of known entities, and a summary list of registered locations.
        """
        state = self.manager.load_latest_state()
        if not state:
            return (
                "No world state initialized yet (Epoch 0). Describe the primordial geography "
                "(oceans, mountain chains, rivers, ancient forests, and rolling plains)."
            )

        epoch = state.get("epoch", 1)
        realm = state.get("realm_name", "Unknown Realm")
        locations = state.get("locations", {})

        types_count: dict[str, int] = {}
        entries: list[str] = []
        for name, data in locations.items():
            ltype = data.get("type", "unknown")
            types_count[ltype] = types_count.get(ltype, 0) + 1
            status = data.get("status", "active")
            if "coord" in data:
                c = data["coord"]
                entries.append(f" - [{ltype.upper()}] {name} at [X: {c[0]:02d}, Y: {c[1]:02d}] (status: {status})")
            elif "tiles" in data:
                tile_count = len(data["tiles"])
                sample_tile = data["tiles"][0] if data["tiles"] else [0, 0]
                entries.append(
                    f" - [{ltype.upper()}] {name} ({tile_count} tiles, near [X: {sample_tile[0]:02d}, Y: {sample_tile[1]:02d}])"
                )

        summary = [
            f"=== WORLD STATE OVERVIEW: {realm} (Epoch {epoch}) ===",
            f"Total Registered Locations: {len(locations)}",
            f"Breakdown: {', '.join(f'{k}: {v}' for k, v in sorted(types_count.items()))}",
            "\nRegistered Locations:",
        ]
        summary.extend(entries[:50])
        return "\n".join(summary)

    def inspect_map(
        self,
        x_min: int = 0,
        y_min: int = 0,
        x_max: int = 31,
        y_max: int = 31,
    ) -> str:
        """Renders the ASCII world map for the specified bounding box (default: entire 32x32 map)

        with stacked 2-digit column headers and 2-digit row headers.

        Args:
            x_min: Minimum X coordinate (0-31).
            y_min: Minimum Y coordinate (0-31).
            x_max: Maximum X coordinate (0-31).
            y_max: Maximum Y coordinate (0-31).
        """
        state = self.manager.load_latest_state()
        if not state:
            return "No map available yet (Epoch 0). Please describe the primordial geography."

        grid = state.get("grid")
        if not grid:
            return "Map grid is empty."

        epoch = state.get("epoch", 1)
        realm = state.get("realm_name", "Unknown Realm")
        rendered = render_ascii_map(grid, x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
        return f"=== MAP: {realm} (Epoch {epoch}) ===\n{rendered}"

    def get_location_details(self, name: str) -> str:
        """Fetches detailed information about a specific registered location.

        Args:
            name: Exact name of the location to query.
        """
        state = self.manager.load_latest_state()
        if not state:
            return "No world state initialized."

        locations = state.get("locations", {})
        # Case-insensitive lookup
        matched_key = next((k for k in locations if k.lower() == name.lower()), None)
        if not matched_key:
            available = list(locations.keys())[:15]
            return f"Location '{name}' not found. Available locations include: {', '.join(available)}"

        data = locations[matched_key]
        return f"Location: {matched_key}\n" + json.dumps(data, indent=2)

    def inspect_tile(self, x: int, y: int) -> str:
        """Inspects a specific coordinate on the world map.

        Args:
            x: X coordinate (0-31).
            y: Y coordinate (0-31).
        """
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            return f"Coordinate ({x}, {y}) out of bounds (0-31)."

        state = self.manager.load_latest_state()
        if not state or not state.get("grid"):
            return "No world state initialized."

        symbol = state["grid"][y][x]
        desc = LEGEND.get(symbol, "Unknown Symbol")

        # Check registered locations
        occupants: list[str] = []
        for name, data in state.get("locations", {}).items():
            if "coord" in data and data["coord"] == [x, y]:
                occupants.append(f"{name} ({data.get('type')})")
            elif "tiles" in data and [x, y] in data["tiles"]:
                occupants.append(f"{name} ({data.get('type')})")

        occupant_str = f"; Occupied by: {', '.join(occupants)}" if occupants else ""
        return f"Tile at [X: {x:02d}, Y: {y:02d}]: Symbol '{symbol}' ({desc}){occupant_str}"


class CartographerTools:
    """Tools available to the Cartographer agent for mutating and snapshotting world state."""

    def __init__(self, manager: WorldStateManager) -> None:
        self.manager = manager
        # In-memory working copy before committing
        self._working_state: Optional[dict[str, Any]] = None

    def _get_active_state(self) -> dict[str, Any]:
        if self._working_state is None:
            latest = self.manager.load_latest_state()
            if latest:
                # Deep copy to allow staging changes
                self._working_state = json.loads(json.dumps(latest))
            else:
                self._working_state = self.manager.get_working_state()
        return self._working_state

    def inspect_map(
        self,
        x_min: int = 0,
        y_min: int = 0,
        x_max: int = 31,
        y_max: int = 31,
    ) -> str:
        """Renders the current working ASCII map with stacked headers."""
        state = self._get_active_state()
        grid = state.get("grid")
        if not grid:
            return "Grid is empty."
        return render_ascii_map(grid, x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)

    def get_world_overview(self) -> str:
        """Returns summary of current working state."""
        state = self._get_active_state()
        epoch = state.get("epoch", 0)
        realm = state.get("realm_name", "Unknown Realm")
        locations = state.get("locations", {})
        return (
            f"Working World State: {realm} (Epoch {epoch})\n"
            f"Total Locations in Registry: {len(locations)}"
        )

    def inspect_tile(self, x: int, y: int) -> str:
        """Inspects what terrain and entities exist at a specific coordinate."""
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            return f"Coordinate ({x}, {y}) out of bounds."
        state = self._get_active_state()
        symbol = state["grid"][y][x]
        desc = LEGEND.get(symbol, "Unknown")
        return f"Tile at [X: {x:02d}, Y: {y:02d}]: '{symbol}' ({desc})"

    def get_location_details(self, name: str) -> str:
        """Fetches detailed information about a specific registered location in the working state.

        Args:
            name: Exact name of the location to query.
        """
        state = self._get_active_state()
        locations = state.get("locations", {})
        matched_key = next((k for k in locations if k.lower() == name.lower()), None)
        if not matched_key:
            available = list(locations.keys())[:15]
            return f"Location '{name}' not found. Available locations include: {', '.join(available)}"
        data = locations[matched_key]
        return f"Location: {matched_key}\n" + json.dumps(data, indent=2)

    def initialize_world(
        self,
        realm_name: str,
        grid_ascii: str,
        locations_json: str,
    ) -> str:
        """Initializes Epoch 1 (Primordial State) from a 32x32 ASCII grid and initial locations registry.

        Saves world_epoch_1.json and overwrites world_epoch_latest.json.

        Args:
            realm_name: Name of the world or continent (e.g. 'Edrath').
            grid_ascii: 32 lines representing the 32x32 grid symbols.
            locations_json: JSON string mapping location names to metadata.
        """
        try:
            grid = parse_grid_text(grid_ascii)
        except Exception as e:
            return f"Error parsing grid_ascii: {e}"

        locations: dict[str, Any] = {}
        if locations_json:
            try:
                if isinstance(locations_json, dict):
                    locations = locations_json
                else:
                    locations = json.loads(locations_json)
            except Exception as e:
                return f"Error parsing locations_json: {e}"

        epoch_path, latest_path = self.manager.save_epoch(
            epoch=1,
            realm_name=realm_name,
            grid=grid,
            locations=locations,
            history_notes="Primordial geography established.",
        )
        self._working_state = None  # Reset working copy to match saved

        rendered = render_ascii_map(grid)
        return (
            f"✅ Epoch 1 Primordial State initialized successfully!\n"
            f"Saved snapshots to:\n - {epoch_path.name}\n - {latest_path.name}\n\n"
            f"Rendered Map:\n{rendered}"
        )

    def add_point_location(
        self,
        name: str,
        location_type: str,
        x: int,
        y: int,
        symbol: str,
        description: str = "",
    ) -> str:
        """Adds or updates a point location (settlement 'o'/'O', dungeon '!', landmark) on the map.

        Args:
            name: Exact name of the location.
            location_type: Type of location ('outpost', 'city', 'dungeon', 'stronghold').
            x: X coordinate (0-31).
            y: Y coordinate (0-31).
            symbol: Single ASCII character representing the entity (e.g. 'o', 'O', '!').
            description: Narrative background or founding motivation.
        """
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            return f"Error: Coordinate ({x}, {y}) is out of bounds (0-31)."
        if symbol not in VALID_SYMBOLS:
            return f"Error: Symbol '{symbol}' is not a valid map legend symbol."

        state = self._get_active_state()
        old_symbol = state["grid"][y][x]
        state["grid"][y][x] = symbol

        state["locations"][name] = {
            "type": location_type,
            "symbol": symbol,
            "coord": [x, y],
            "status": "active",
            "description": description,
        }
        return f"Placed '{name}' ({location_type}) at [X: {x:02d}, Y: {y:02d}] with symbol '{symbol}' (replaced '{old_symbol}')."

    def modify_terrain(
        self,
        coords: list[list[int]],
        symbol: str,
        region_name: str = "",
    ) -> str:
        """Modifies terrain tiles for deforestation, swamp draining, irrigation, or blighting.

        Args:
            coords: List of [x, y] coordinate pairs to update.
            symbol: New terrain symbol (e.g. '.' for cleared plains, ':' for farmland, '*' for wasteland).
            region_name: Optional name of existing region in locations to update its tile list.
        """
        if symbol not in VALID_SYMBOLS:
            return f"Error: Symbol '{symbol}' is not in the map legend."

        state = self._get_active_state()
        grid = state["grid"]
        updated_count = 0

        for pair in coords:
            if len(pair) == 2:
                x, y = pair[0], pair[1]
                if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
                    grid[y][x] = symbol
                    updated_count += 1

        if region_name and region_name in state["locations"]:
            reg = state["locations"][region_name]
            if "tiles" in reg:
                # Remove coords if they were converted away from the region's native symbol
                reg_symbol = reg.get("symbol")
                if reg_symbol and symbol != reg_symbol:
                    reg["tiles"] = [t for t in reg["tiles"] if t not in coords]
                elif reg_symbol and symbol == reg_symbol:
                    for c in coords:
                        if c not in reg["tiles"]:
                            reg["tiles"].append(c)

        return f"Modified {updated_count} tiles to '{symbol}' ({LEGEND.get(symbol, '')})."

    def build_road(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        road_name: str,
    ) -> str:
        """Builds an organic road/trade route connecting two points using terrain-weighted A*.

        Places bridges '=' over water '~' and roads '+' over land.

        Args:
            start_x: Starting X coordinate.
            start_y: Starting Y coordinate.
            end_x: Ending X coordinate.
            end_y: Ending Y coordinate.
            road_name: Name of the route (e.g. 'Oris-Vael Track').
        """
        state = self._get_active_state()
        grid = state["grid"]

        path = find_path_astar(grid, (start_x, start_y), (end_x, end_y))
        if not path:
            return f"Error: Could not find passable path from ({start_x}, {start_y}) to ({end_x}, {end_y}) (blocked by mountains)."

        road_tiles: list[list[int]] = []
        bridges: int = 0
        roads: int = 0

        # Don't overwrite endpoint settlement symbols if they are cities/outposts
        for x, y in path:
            current = grid[y][x]
            if (x, y) in ((start_x, start_y), (end_x, end_y)) and current in ("o", "O", "!"):
                road_tiles.append([x, y])
                continue

            if current == "~":
                grid[y][x] = "="
                bridges += 1
            else:
                grid[y][x] = "+"
                roads += 1
            road_tiles.append([x, y])

        state["locations"][road_name] = {
            "type": "road",
            "symbol": "+",
            "tiles": road_tiles,
            "status": "active",
            "description": f"Trade route connecting ({start_x}, {start_y}) to ({end_x}, {end_y}).",
        }
        return f"Built road '{road_name}' ({len(road_tiles)} tiles: {roads} road tiles, {bridges} bridges)."

    def update_location_status(
        self,
        name: str,
        new_status: str,
        new_symbol: str = "",
        decay_roads: bool = True,
    ) -> str:
        """Updates the status and symbol of a location (e.g. city fell to ruin '!').

        If new_status is 'ruined' or symbol is '!', optionally decays connecting roads.

        Args:
            name: Name of the location.
            new_status: Status string (e.g. 'ruined', 'abandoned', 'thriving').
            new_symbol: Optional new symbol (e.g. '!' for dungeon/ruin).
            decay_roads: If True and location is ruined, decays ~50% of connecting road tiles back to native terrain.
        """
        state = self._get_active_state()
        matched = next((k for k in state["locations"] if k.lower() == name.lower()), None)
        if not matched:
            return f"Error: Location '{name}' not found."

        loc = state["locations"][matched]
        loc["status"] = new_status
        decayed_tiles = 0

        if new_symbol:
            loc["symbol"] = new_symbol
            if "coord" in loc:
                cx, cy = loc["coord"]
                state["grid"][cy][cx] = new_symbol

        if decay_roads and (new_status in ("ruined", "abandoned") or new_symbol == "!"):
            if "coord" in loc:
                cx, cy = loc["coord"]
                grid = state["grid"]
                # Look for adjacent road tiles
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                    ax, ay = cx + dx, cy + dy
                    if 0 <= ax < GRID_WIDTH and 0 <= ay < GRID_HEIGHT:
                        if grid[ay][ax] == "+":
                            # 50% chance of decaying back to wilderness
                            if random.random() < 0.5:
                                grid[ay][ax] = "."
                                decayed_tiles += 1

        return f"Updated '{matched}' to status='{new_status}', symbol='{new_symbol}'. Decayed {decayed_tiles} connecting road tiles."

    def commit_epoch_snapshot(self, epoch: int, notes: str = "") -> str:
        """Commits all staged updates to world_epoch_{epoch}.json and overwrites world_epoch_latest.json.

        Args:
            epoch: Epoch number to save (e.g. 2, 3...).
            notes: Brief summary of historical developments and cartographic shifts.
        """
        state = self._get_active_state()
        realm_name = state.get("realm_name", "Edrath")
        grid = state["grid"]
        locations = state["locations"]

        epoch_path, latest_path = self.manager.save_epoch(
            epoch=epoch,
            realm_name=realm_name,
            grid=grid,
            locations=locations,
            history_notes=notes,
        )
        self._working_state = None  # Clear working state

        rendered = render_ascii_map(grid)
        return (
            f"✅ Epoch {epoch} snapshot successfully committed!\n"
            f"Files updated:\n - {epoch_path.name}\n - {latest_path.name}\n\n"
            f"Current Map:\n{rendered}"
        )
