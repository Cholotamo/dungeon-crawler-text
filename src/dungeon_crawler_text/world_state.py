"""World state management for the Dungeon Crawler simulation.

Manages persistent world snapshots (e.g. world_epoch_1.json, world_epoch_latest.json),
32x32 ASCII grid matrix parsing and rendering, and spatial locations registry.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional


LEGEND: dict[str, str] = {
    ".": "Open Plains / Wilderness",
    ",": "Hills / Slopes",
    "#": "Forest / Woods",
    "&": "Dense Forest / Deep Jungle",
    "%": "Swamp / Bog / Marsh",
    "~": "Water / River / Ocean",
    ";": "Coast / Beach / Shallows",
    "^": "Mountain Peak / Ridge",
    "/": "Cliffs / Edges / Chasms",
    "+": "Active Road / Trade Route",
    "=": "Bridge / River Crossing",
    "o": "Small Settlement / Outpost",
    "O": "Major City / Metropolis",
    "*": "Wastelands",
    ":": "Farmland",
    "!": "Dungeon / Ruined City / Beast Den / Stronghold",
}

VALID_SYMBOLS: set[str] = set(LEGEND.keys())
GRID_WIDTH = 32
GRID_HEIGHT = 32


def render_ascii_map(
    grid: list[list[str]],
    x_min: int = 0,
    y_min: int = 0,
    x_max: int = 31,
    y_max: int = 31,
) -> str:
    """Renders the grid as a formatted ASCII map with stacked 2-digit X headers

    and 2-digit Y row headers.
    """
    x_min = max(0, min(x_min, GRID_WIDTH - 1))
    x_max = max(0, min(x_max, GRID_WIDTH - 1))
    y_min = max(0, min(y_min, GRID_HEIGHT - 1))
    y_max = max(0, min(y_max, GRID_HEIGHT - 1))

    if x_min > x_max:
        x_min, x_max = x_max, x_min
    if y_min > y_max:
        y_min, y_max = y_max, y_min

    cols = range(x_min, x_max + 1)
    lines: list[str] = []

    # Stacked 2-digit column headers (tens on top, ones below) offset by 3 spaces
    lines.append("   " + " ".join(f"{x // 10}" for x in cols))
    lines.append("   " + " ".join(f"{x % 10}" for x in cols))

    for y in range(y_min, y_max + 1):
        row_str = " ".join(grid[y][x] for x in cols)
        lines.append(f"{y:02d} {row_str}")

    return "\n".join(lines)


def parse_grid_text(grid_text: str) -> list[list[str]]:
    """Parses text containing a 32x32 ASCII grid into a 2D list of characters.

    Robustly handles lines with row numbers (e.g. '00 ~ ~ ...' or '0: ~ ~ ...'),
    header lines, trailing whitespace, and variable spacing. Stops once 32 valid
    grid rows are collected.
    """
    raw_lines = [line.strip() for line in grid_text.strip().splitlines() if line.strip()]
    grid_rows: list[list[str]] = []

    for line in raw_lines:
        if len(grid_rows) == GRID_HEIGHT:
            break

        cleaned_line = line
        has_row_prefix = False
        m = re.match(r"^(\d{1,2})[\s:]+(.*)$", line)
        if m:
            row_idx = int(m.group(1))
            # If row numbers match sequential or current expected row
            if row_idx == len(grid_rows):
                has_row_prefix = True
                cleaned_line = m.group(2).strip()

        # Extract tokens
        tokens = cleaned_line.split()
        valid_tokens = [t for t in tokens if t in VALID_SYMBOLS]

        if len(valid_tokens) == GRID_WIDTH:
            grid_rows.append(valid_tokens)
        elif has_row_prefix and len(valid_tokens) > 0:
            # If off by 1-2 tokens, pad or trim
            if abs(len(valid_tokens) - GRID_WIDTH) <= 2:
                if len(valid_tokens) < GRID_WIDTH:
                    pad = valid_tokens[-1] if valid_tokens else "."
                    valid_tokens.extend([pad] * (GRID_WIDTH - len(valid_tokens)))
                else:
                    valid_tokens = valid_tokens[:GRID_WIDTH]
                grid_rows.append(valid_tokens)
            else:
                char_tokens = [c for c in cleaned_line if c in VALID_SYMBOLS]
                if len(char_tokens) == GRID_WIDTH:
                    grid_rows.append(char_tokens)
                elif abs(len(char_tokens) - GRID_WIDTH) <= 2:
                    if len(char_tokens) < GRID_WIDTH:
                        pad = char_tokens[-1] if char_tokens else "."
                        char_tokens.extend([pad] * (GRID_WIDTH - len(char_tokens)))
                    else:
                        char_tokens = char_tokens[:GRID_WIDTH]
                    grid_rows.append(char_tokens)

    if len(grid_rows) != GRID_HEIGHT:
        raise ValueError(
            f"Expected {GRID_HEIGHT} rows of {GRID_WIDTH} symbols, but parsed {len(grid_rows)} valid rows. "
            f"Total input lines were {len(raw_lines)}."
        )

    return grid_rows


def create_empty_grid(default_symbol: str = ".") -> list[list[str]]:
    """Creates a 32x32 empty grid filled with default_symbol."""
    return [[default_symbol for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]


class WorldStateManager:
    """Manages reading, mutating, and snapshotting the persistent world state.

    The state is maintained in JSON files:
    - world_epoch_{epoch}.json (snapshot of each epoch)
    - world_epoch_latest.json (overwriting copy of the latest epoch)
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or (Path.cwd() / "artifacts" / "world_state")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_state: Optional[dict[str, Any]] = None
        self._load_latest_on_init()

    @property
    def latest_file_path(self) -> Path:
        return self.storage_dir / "world_epoch_latest.json"

    def epoch_file_path(self, epoch: int) -> Path:
        return self.storage_dir / f"world_epoch_{epoch}.json"

    def _load_latest_on_init(self) -> None:
        """Loads world_epoch_latest.json if present on disk."""
        if self.latest_file_path.exists():
            try:
                self._current_state = json.loads(
                    self.latest_file_path.read_text(encoding="utf-8")
                )
            except Exception:
                self._current_state = None

    def get_latest_epoch_number(self) -> int:
        """Returns the highest epoch number found in storage, or 0 if none exist."""
        if self._current_state and "epoch" in self._current_state:
            return int(self._current_state["epoch"])

        highest = 0
        for p in self.storage_dir.glob("world_epoch_*.json"):
            m = re.match(r"^world_epoch_(\d+)\.json$", p.name)
            if m:
                highest = max(highest, int(m.group(1)))
        return highest

    def load_latest_state(self) -> Optional[dict[str, Any]]:
        """Loads and returns the latest world state dictionary, or None if uninitialized."""
        if self.latest_file_path.exists():
            data = json.loads(self.latest_file_path.read_text(encoding="utf-8"))
            self._current_state = data
            return data

        # Fallback: check for highest numbered epoch
        latest_num = self.get_latest_epoch_number()
        if latest_num > 0:
            p = self.epoch_file_path(latest_num)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                self._current_state = data
                # Re-sync world_epoch_latest.json
                self.latest_file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return data

        return None

    def load_epoch_state(self, epoch: int) -> Optional[dict[str, Any]]:
        """Loads and returns a specific epoch state."""
        p = self.epoch_file_path(epoch)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def get_working_state(self) -> dict[str, Any]:
        """Returns the current in-memory working state or initializes a blank one."""
        if self._current_state is None:
            self._current_state = {
                "epoch": 0,
                "realm_name": "Unknown Realm",
                "grid": create_empty_grid(),
                "locations": {},
                "history_log": [],
            }
        return self._current_state

    def save_epoch(
        self,
        epoch: int,
        realm_name: str,
        grid: list[list[str]],
        locations: dict[str, Any],
        history_notes: str = "",
    ) -> tuple[Path, Path]:
        """Saves world state to world_epoch_{epoch}.json and overwrites world_epoch_latest.json."""
        if len(grid) != GRID_HEIGHT or any(len(row) != GRID_WIDTH for row in grid):
            raise ValueError(
                f"Invalid grid dimensions. Must be {GRID_WIDTH}x{GRID_HEIGHT}."
            )

        # Append to history log if notes provided
        history_log = list(self.get_working_state().get("history_log", []))
        if history_notes:
            history_log.append({"epoch": epoch, "summary": history_notes})

        state = {
            "epoch": epoch,
            "realm_name": realm_name,
            "grid": grid,
            "locations": locations,
            "history_log": history_log,
        }

        self._current_state = state

        # 1. Write epoch snapshot
        epoch_path = self.epoch_file_path(epoch)
        json_content = json.dumps(state, indent=2)
        epoch_path.write_text(json_content, encoding="utf-8")

        # 2. Overwrite latest snapshot
        latest_path = self.latest_file_path
        latest_path.write_text(json_content, encoding="utf-8")

        return epoch_path, latest_path

    def render_current_map(
        self,
        x_min: int = 0,
        y_min: int = 0,
        x_max: int = 31,
        y_max: int = 31,
    ) -> str:
        """Renders ASCII map of the current state."""
        state = self.load_latest_state() or self.get_working_state()
        return render_ascii_map(state["grid"], x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
