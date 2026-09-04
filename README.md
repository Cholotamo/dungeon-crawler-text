# Dungeon Crawler Text: World-Building Simulation

A multi-agent generative world-building simulation powered by Gemini. A **Historian** and a **Cartographer** agent collaborate across epochs to chronicle the rise, evolution, and transformation of a fantasy realm represented as an ASCII dual-grid map.

---

## Prerequisites

- **Python:** `>= 3.14`
- **Package Manager:** [`uv`](https://github.com/astral-sh/uv)
- **Gemini API Key:** Set in a `.env` file in the project root:
  ```env
  GEMINI_API_KEY=your_api_key_here
  ```

---

## Installation & Setup

Install dependencies and set up the virtual environment using `uv`:

```bash
uv sync
```

---

## Running the Simulation

Run the simulation via the package entry point:

```bash
uv run dungeon-crawler-text
```

Alternatively, invoke the module directly with Python:

```bash
uv run python -m dungeon_crawler_text.main
```

---

## CLI Options

Customize the simulation using command-line arguments:

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--turns` | `int` | `2` | Number of historical epochs to simulate |
| `--model` | `str` | `gemini-3.7-flash` | Gemini model to use for both agents |
| `--thinking` | `str` | `HIGH` | Thinking budget / level (`HIGH`, `LOW`, etc.) |
| `--artifacts` | `str` | `artifacts` | Directory where snapshot JSON files are saved |

### Examples

- **Simulate 4 epochs:**
  ```bash
  uv run dungeon-crawler-text --turns 4
  ```

- **Use a custom model and artifacts directory:**
  ```bash
  uv run dungeon-crawler-text --turns 3 --model gemini-3.7-flash --artifacts custom_artifacts
  ```

---

## How It Works

1. **Turn 1 (Primordial Canvas):**
   - The **Cartographer** queries the **Historian** to establish the origins of the world.
   - The **Historian** writes the primordial narrative.
   - The **Cartographer** executes procedural Python code to generate the initial 32×32 dual-grid world map (terrain and region IDs).

2. **Turn 2+ (Chronicle Evolution):**
   - The **Historian** inspects the current dual-grid world state, cartographic logs, and past narrative memory to recount the passage of time and historical events.
   - The Python runner clones and initializes the snapshot file for the new epoch.
   - The **Cartographer** evolves the world map statelessly using fine-grained mutation tools via Gemini Automatic Function Calling (AFC):
     - `set_tiles` / `fill_area`: Terrain and biome modifications.
     - `upsert_landmark` / `remove_landmark`: Founding, upgrading, or destroying settlements and dungeons.
     - `upsert_road` / `decay_road`: Road paving and degradation.
     - `upsert_region`: Biome and territory registrations.

3. **Output & Artifacts:**
   - Visual ASCII composite maps with stacked coordinates are printed to the terminal each epoch.
   - Epoch snapshots are saved as JSON files in the `artifacts/` folder (`world_state_epoch_{epoch}.json`).
   - A token usage summary is reported at the end of each run.
