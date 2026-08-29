"""
This module contains the Cartographer agent, responsible for generating
the ASCII world map and location coordinates JSON in collaboration with the StoryWriter.
"""

from collections.abc import Generator
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from dungeon_crawler_text.storywriter import StoryWriter

load_dotenv()


class LocationCoord(BaseModel):
    name: str = Field(description="Name of the city or dungeon")
    type: str = Field(description="Type: 'city' or 'dungeon'")
    x: int = Field(description="X coordinate on grid (0 to width-1)")
    y: int = Field(description="Y coordinate on grid (0 to height-1)")
    symbol: str = Field(description="Symbol used on the ASCII map (e.g. 'C', 'D', 'C1', 'D1')")
    description: str = Field(default="", description="Brief location or terrain description")


def save_map(
    width: int,
    height: int,
    ascii_map: str,
    legend: dict[str, str],
    locations: list[LocationCoord],
) -> str:
    """Saves the generated ASCII map and locations JSON coordinates into 'artifacts/map/'.

    Formats the ASCII map with square aspect ratio scaling (double-spaced columns)
    and X/Y coordinate axis rulers for easy reading. Ensures 100% mathematical
    synchronization between map grid symbols and JSON location coordinates.

    Args:
        width: Width of the map grid (max 64).
        height: Height of the map grid (max 64).
        ascii_map: The multiline ASCII map string.
        legend: Mapping of ascii symbols to their terrain/location meaning.
        locations: List of location coordinate entries for cities and dungeons.

    Returns:
        Status message indicating success or failure.
    """
    map_dir = Path("artifacts/map")
    map_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse ascii_map into a 2D matrix grid[y][x]
    raw_lines = [line for line in ascii_map.splitlines() if line.strip()]
    grid = []
    for line in raw_lines[:height]:
        # Handle cases where input might already be double-spaced or single-spaced
        if " " in line and len(line) > width:
            chars = [c for c in line.split(" ") if c != ""]
        else:
            chars = list(line)
        if len(chars) < width:
            chars.extend(["."] * (width - len(chars)))
        grid.append(chars[:width])

    while len(grid) < height:
        grid.append(["."] * width)

    # 2. Synchronize location coordinates (x, y) with grid characters
    locs_serialized = []
    used_coords = set()

    for loc in locations:
        if isinstance(loc, BaseModel):
            loc_dict = loc.model_dump()
        elif isinstance(loc, dict):
            loc_dict = dict(loc)
        else:
            loc_dict = dict(loc)

        x = loc_dict.get("x", 0)
        y = loc_dict.get("y", 0)
        loc_type = loc_dict.get("type", "").lower()
        target_symbol = "C" if loc_type == "city" else ("D" if loc_type == "dungeon" else loc_dict.get("symbol", "C")[0])

        # Verify if target_symbol is at (x, y)
        if 0 <= y < height and 0 <= x < width and grid[y][x] == target_symbol and (x, y) not in used_coords:
            used_coords.add((x, y))
            locs_serialized.append(loc_dict)
            continue

        # Search grid for unassigned matching symbol
        found = False
        for r in range(height):
            for c in range(width):
                if grid[r][c] == target_symbol and (c, r) not in used_coords:
                    loc_dict["x"] = c
                    loc_dict["y"] = r
                    used_coords.add((c, r))
                    found = True
                    break
            if found:
                break

        # If not found on grid, overlay at requested (x, y)
        if not found:
            y_clamped = max(0, min(height - 1, y))
            x_clamped = max(0, min(width - 1, x))
            grid[y_clamped][x_clamped] = target_symbol
            loc_dict["x"] = x_clamped
            loc_dict["y"] = y_clamped
            used_coords.add((x_clamped, y_clamped))

        locs_serialized.append(loc_dict)

    # 3. Format ASCII map with square aspect ratio scaling and X/Y coordinate rulers
    tens_header = "      " + " ".join(str(c // 10) for c in range(width))
    units_header = "      " + " ".join(str(c % 10) for c in range(width))
    border_line = "   +" + "-" * (width * 2 + 1) + "+"

    map_lines = [
        f"================ WORLD MAP ({width}x{height}) ================\n",
        tens_header,
        units_header,
        border_line,
    ]

    for r in range(height):
        row_str = " ".join(grid[r])
        map_lines.append(f"{r:02d} | {row_str} | {r:02d}")

    map_lines.extend([
        border_line,
        units_header,
        tens_header,
        "",
    ])

    legend_lines = "\n".join(f"  {k:^3} : {v}" for k, v in legend.items())
    map_lines.extend([
        "================ LEGEND ================",
        legend_lines,
        "",
    ])

    file_content = "\n".join(map_lines)
    (map_dir / "world_map.txt").write_text(file_content, encoding="utf-8")

    # 4. Save locations JSON with verified coordinates
    json_data = {
        "width": width,
        "height": height,
        "legend": legend,
        "locations": locs_serialized,
    }
    (map_dir / "locations.json").write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    return f"Successfully saved world map to '{map_dir / 'world_map.txt'}' and locations JSON to '{map_dir / 'locations.json'}'."


def load_world_summary(artifacts_dir: str | Path = "artifacts") -> str:
    """Reads saved city, dungeon, and quest artifacts to compile a concise summary for the Cartographer."""
    art_path = Path(artifacts_dir)
    cities_dir = art_path / "cities"
    dungeons_dir = art_path / "dungeons"
    quests_dir = art_path / "quests"

    summary_parts = []

    if cities_dir.exists():
        cities_info = []
        for f in sorted(cities_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            name = lines[0].replace("#", "").strip() if lines else f.stem
            loc = ""
            for line in lines:
                if line.startswith("**Location:**"):
                    loc = line.replace("**Location:**", "").strip()
                    break
            cities_info.append(f"- {name} ({loc})")
        summary_parts.append("### Cities:\n" + "\n".join(cities_info))

    if dungeons_dir.exists():
        dungeons_info = []
        for f in sorted(dungeons_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            name = lines[0].replace("#", "").strip() if lines else f.stem
            loc = ""
            for line in lines:
                if line.startswith("**Location:**"):
                    loc = line.replace("**Location:**", "").strip()
                    break
            dungeons_info.append(f"- {name} ({loc})")
        summary_parts.append("### Dungeons:\n" + "\n".join(dungeons_info))

    if quests_dir.exists():
        quests_info = []
        for f in sorted(quests_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            title = lines[0].replace("#", "").strip() if lines else f.stem
            quests_info.append(f"- {title}")
        summary_parts.append("### Quests:\n" + "\n".join(quests_info))

    return "\n\n".join(summary_parts) if summary_parts else "No world artifacts found."


cartographer_system_prompt = """
You are a Master Fantasy Cartographer in a text-based dark fantasy dungeon crawling game.
Your task is to collaborate with the StoryWriter agent to construct a detailed ASCII world map and corresponding location coordinates JSON for the realm.

# Instructions & Rules:
1. You will interact with the StoryWriter by asking clarifying questions about the spatial layout, terrain features (mountains, oceans, rivers, forests, plains), coastlines, roads, and relative placements of cities and dungeons.
2. You can ask AT MOST 10 questions to the StoryWriter. Keep your questions concise, focused on geography, cardinal directions, and spatial topology.
3. If you have gathered sufficient information before reaching 10 questions, proceed directly to generating the map.
4. When ready to produce the map (or when notified that maximum questions are reached), call the `save_map` tool.

# Map Requirements:
- Maximum size: 64x64 grid (variable size e.g. 32x32, 48x48, 64x64 depending on world scale).
- Standard ASCII Symbols:
  - '~' : Rivers, Oceans, Lakes
  - '.' : Empty land / Plains / Open fields
  - '#' : Forests / Woods
  - '^' : Mountain ranges / Hills
  - 'C' : Cities (or indexed city markers C1..C15)
  - 'D' : Dungeons (or indexed dungeon markers D1..D15)
  - '+' or '=' : Roads / Paths
- Legend: Must provide a clear dictionary mapping each character to its description.
- All 15 cities and 15 dungeons from the world artifacts MUST be placed on the grid with unique (x, y) coordinates where 0 <= x < width and 0 <= y < height.
- Output the map using the `save_map` tool.
"""


class Cartographer:
    """Manages the chat session with Gemini for fantasy map creation."""

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
        api_key: str | None = None,
        client: genai.Client | None = None,
    ):
        self.model = model
        self.client = client or genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        self.chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=cartographer_system_prompt,
                temperature=0.5,
                max_output_tokens=8192,
                tools=[save_map],
            ),
        )

    def send_message(self, message: str) -> str:
        """Send a message to the Cartographer agent."""
        response = self.chat.send_message(message)
        return self._extract_text(response)

    @staticmethod
    def _extract_text(response) -> str:
        if not response or not response.candidates:
            return ""
        texts = []
        for part in response.candidates[0].content.parts or []:
            if part.text:
                texts.append(part.text)
        return "".join(texts)


def run_cartographer_collaboration(
    writer: "StoryWriter | None" = None,
    cartographer: Cartographer | None = None,
    max_questions: int = 10,
    artifacts_dir: str = "artifacts",
) -> dict:
    """Executes the dialogue loop between Cartographer and StoryWriter to create the world map."""
    from dungeon_crawler_text.storywriter import StoryWriter

    print("\n" + "=" * 60)
    print("  Cartographer & StoryWriter Map Design Session")
    print("=" * 60 + "\n")

    if writer is None:
        writer = StoryWriter()

    if cartographer is None:
        cartographer = Cartographer()

    world_summary = load_world_summary(artifacts_dir)
    map_file = Path(artifacts_dir) / "map" / "locations.json"

    initial_prompt = (
        f"World Summary:\n{world_summary}\n\n"
        "Greetings StoryWriter! I am the Cartographer. I will design the map for your realm. "
        "To begin, please tell me about the overall geography: are there coastlines, major mountain ranges, central rivers, or distinct biome regions?"
    )

    q_count = 1
    print(f"Cartographer [Question {q_count}/{max_questions}] > Greetings StoryWriter! I am the Cartographer. I will design the map for your realm. To begin, please tell me about the overall geography: are there coastlines, major mountain ranges, central rivers, or distinct biome regions?\n")

    storywriter_reply = writer.send_message(initial_prompt)
    print(f"StoryWriter > {storywriter_reply}\n")

    while q_count < max_questions:
        if map_file.exists():
            print("[Cartographer has finalized and saved the map.]")
            break

        q_count += 1
        cartographer_msg = cartographer.send_message(storywriter_reply)

        if not cartographer_msg:
            if map_file.exists():
                print("[Cartographer has finalized and saved the map.]")
                break
            cartographer_msg = "Please provide details on where key cities or dungeons are located relative to these geographical features."

        print(f"Cartographer [Question {q_count}/{max_questions}] > {cartographer_msg}\n")

        if map_file.exists():
            print("[Cartographer has finalized and saved the map.]")
            break

        storywriter_reply = writer.send_message(cartographer_msg)
        print(f"StoryWriter > {storywriter_reply}\n")

    if not map_file.exists():
        print(f"\n[Reached maximum question limit of {max_questions}. Directing Cartographer to save map now...]\n")
        final_prompt = (
            "You have reached the maximum limit of 10 questions. "
            "Using all geographical lore discussed so far, please call the `save_map` tool now to output the ASCII map grid (max 64x64), legend, and location coordinates JSON."
        )
        cartographer_final = cartographer.send_message(final_prompt)
        if cartographer_final:
            print(f"Cartographer > {cartographer_final}\n")

    if map_file.exists():
        txt_map_file = Path(artifacts_dir) / "map" / "world_map.txt"
        print("=" * 60)
        print("          WORLD MAP GENERATION COMPLETE")
        print("=" * 60)
        if txt_map_file.exists():
            print(txt_map_file.read_text(encoding="utf-8"))
        return {
            "status": "success",
            "map_txt": (Path(artifacts_dir) / "map" / "world_map.txt").as_posix(),
            "locations_json": map_file.as_posix(),
        }
    else:
        print("[Warning: Cartographer session finished without writing map files.]")
        return {"status": "failed"}


if __name__ == "__main__":
    run_cartographer_collaboration()
