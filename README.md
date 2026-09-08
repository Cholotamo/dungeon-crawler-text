# Dungeon Crawler Text: Primordial World-Building Pipeline

A generative fantasy world-building pipeline powered by Gemini. The pipeline operates in two coordinated stages to craft living, mythic fantasy realms from dawn-of-time lore down to a concrete 32x32 cartographic world map:

1. **The Loremaster:** Synthesizes evocative, mythic narrative prose describing the untouched primordial landscape and raw physical geography of a realm at the dawn of creation.
2. **The Architect:** Translates the primordial world prose into a structured 32x32 ASCII and JSON world map using Gemini with **Python Code Execution**, enforcing organic biome geography and strict hydrological rules.
3. **The Historian:** Chronicles the passage of historical epochs, translating narrative developments into physical changes on the map using fine-grained **Feature CRUD Tools** via Gemini Automatic Function Calling (AFC).

```
                    ┌─────────────────────────┐
                    │   Primordial Prompt /   │
                    │          Query          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       Loremaster        │
                    │  (gemini-3.6-flash)     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ artifacts/worldprose.md │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        Architect        │
                    │ (LLM + Code Execution)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ artifacts/worldmap.json │
                    │ artifacts/worldmap.md   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        Historian        │
                    │   (Feature CRUD Tools)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ artifacts/              │
                    │   worldmap_epoch_1.json │
                    │   worldmap_epoch_1.md   │
                    │   worldmap_epoch_n...   │
                    └─────────────────────────┘
```

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

## Running the Pipeline

### Step 1: Generate Primordial World Prose (Loremaster)

Generate the primordial narrative prose using the CLI:

```bash
uv run dungeon-crawler-text
```

Or invoke the module directly:

```bash
uv run python -m dungeon_crawler_text.main
```

#### Loremaster CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model` | `str` | `gemini-3.6-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `MEDIUM` | Thinking budget / level (`HIGH`, `MEDIUM`, `LOW`, etc.) |
| `--query` | `str` | *Default Primordial Query* | Custom prompt query to ask the Loremaster |
| `--output`, `-o` | `str` | `artifacts/worldprose.md` | Path to save the output prose file |

**Examples:**
```bash
# Default run (saves to artifacts/worldprose.md)
uv run dungeon-crawler-text

# Save to custom file
uv run dungeon-crawler-text --output artifacts/custom_world.md

# Custom world query
uv run dungeon-crawler-text --query "Describe a primordial volcanic archipelago of black glass and boiling lagoons."
```

---

### Step 2: Generate 32x32 World Map (Architect)

Translate the generated world prose into a validated 32x32 world map using the Architect:

```bash
uv run python -m dungeon_crawler_text.architect
```

#### Architect CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input`, `-i` | `str` | `artifacts/worldprose.md` | Path to input world prose markdown file |
| `--output`, `-o` | `str` | `artifacts/worldmap.json` | Path to save output world map JSON file |
| `--model` | `str` | `gemini-3.6-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `MEDIUM` | Thinking budget / level (`HIGH`, `MEDIUM`, `LOW`, etc.) |

**Examples:**
```bash
# Default run (reads artifacts/worldprose.md, saves artifacts/worldmap.json)
uv run python -m dungeon_crawler_text.architect

# Custom input and output paths
uv run python -m dungeon_crawler_text.architect -i artifacts/custom_world.md -o artifacts/custom_map.json

# Run with HIGH thinking level
uv run python -m dungeon_crawler_text.architect --thinking HIGH
```

---

### Step 3: Advance Epochs & Mutate Map Features (Historian)

Advance time across historical epochs, founding settlements, paving trade roads, building bridges, and discovering ancient ruins using the Historian agent equipped with **Feature CRUD tools**:

```bash
uv run dungeon-crawler-historian
```

Or invoke via Python module:

```bash
uv run python -m dungeon_crawler_text.historian
```

#### Historian Workflow
- **Turn 1 (Epoch 1):** Takes `artifacts/worldmap.md` as input, creates an active copy `artifacts/worldmap_epoch_1.json`, mutates features via tools, and saves the rendered companion `artifacts/worldmap_epoch_1.md`.
- **Subsequent Turns (Epoch 2+):** Within the same conversation, automatically takes the previous epoch markdown (`worldmap_epoch_1.md`) as input, creates `worldmap_epoch_2.json`, applies further mutations (upgrading settlements to cities `'O'`, paving roads `'+'`, creating dungeons `'!'`), and saves `worldmap_epoch_2.md`.

#### Historian CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input`, `-i` | `str` | *Auto-detect latest epoch* | Input markdown file path |
| `--epochs`, `-n` | `int` | `1` | Number of sequential epochs to advance within the same conversation |
| `--query`, `-q` | `str` | *Epoch Default* | Custom historical prompt or directive for the epoch |
| `--interactive` | `flag` | `False` | Run interactively, prompting for epoch directives within the same conversation |
| `--model` | `str` | `gemini-3.6-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `MEDIUM` | Thinking level for Gemini models (`HIGH`, `MEDIUM`, `LOW`) |

**Examples:**
```bash
# Advance one epoch (takes worldmap.md or latest epoch, saves _epoch_n)
uv run dungeon-crawler-historian

# Run 3 consecutive epochs in a single ongoing conversation
uv run dungeon-crawler-historian --epochs 3

# Run interactive simulation loop
uv run dungeon-crawler-historian --interactive

# Custom historical event query
uv run dungeon-crawler-historian --query "A devastating civil war splits the realm, turning the eastern fortress into a ruined dungeon."
```

---

## Python API

All agents can be imported and executed programmatically:

```python
from dungeon_crawler_text import Architect, Historian, Loremaster

# 1. Generate primordial narrative prose
loremaster = Loremaster(model_name="gemini-3.6-flash", thinking_level="MEDIUM")
prose = loremaster.generate_primordial_world()

# 2. Architect 32x32 world map from prose
architect = Architect(model_name="gemini-3.6-flash", thinking_level="MEDIUM")
world_map = architect.generate_world_map(worldprose=prose)
architect.save_world_map(world_map)

# 3. Advance world history across epochs using the Historian
historian = Historian(model_name="gemini-3.6-flash", thinking_level="MEDIUM")

# Run Epoch 1 (takes worldmap.md, creates worldmap_epoch_1.json and worldmap_epoch_1.md)
res_epoch1 = historian.run_epoch()

# Run Epoch 2 in the same conversation (takes worldmap_epoch_1.md, creates worldmap_epoch_2.json and worldmap_epoch_2.md)
res_epoch2 = historian.run_epoch()
```

---

## Map Structure & Legend

The Architect outputs a structured JSON artifact conforming to the following schema:

```json
{
  "name": "Realm Name from Prose",
  "terrain_grid": [
    "32 strings of exactly 32 terrain chars..."
  ],
  "region_grid": [
    "32 strings of exactly 32 single-character region IDs..."
  ],
  "regions": {
    "0": { "name": "Unnamed Wilderness", "type": "wilderness" },
    "1": { "name": "Iron-Grip Coast", "type": "coastal" },
    "2": { "name": "Skyshear Spine", "type": "mountain" }
  },
  "features": {}
}
```

### Terrain Character Legend

| Char | Terrain Type | Description |
| :---: | :--- | :--- |
| `.` | Plains / Wilderness | Open lowlands and temperate meadows |
| `,` | Hills / Slopes | Rolling uplands and foothills |
| `#` | Forest / Woods | Temperate woodland and copse |
| `&` | Dense Forest / Deep Jungle | Ancient, impenetrable canopy |
| `%` | Swamp / Bog / Marsh | Wetlands, mires, and sodden fens |
| `~` | Water / River / Ocean | Cardinal waterways, seas, and lakes |
| `;` | Coast / Beach / Shallows | Shingle shores, sandbanks, and tidal reaches |
| `^` | Mountain Peak / Ridge | Towering alpine peaks and jagged crests |
| `/` | Cliffs / Edges / Chasms | Precipitous escarpments and fissures |
| `*` | Wastelands | Blighted, volcanic, or desolate wastes |
| `:` | Farmland | Arable agricultural lands |

---

## Architecture & How It Works

1. **Loremaster (`loremaster.py` & `prompts/loremaster_worldprose.md`):**
   - Anchors the model in high-fantasy mythic world-building (Tolkien + Kentaro Miura).
   - Restricts focus purely to macro-geography: ridgelines, coastlines, river basins, and primal ecosystems before mortal civilization or settlements.

2. **Architect (`architect.py` & `prompts/architect_worldmap.md`):**
   - **Python Code Execution:** Operates with Gemini code execution enabled. The model writes and runs procedural Python code (using cellular smoothing, noise, and distance heuristics) to ensure natural, organic landmasses rather than artificial straight lines or blocks.
   - **Hydrological Continuity:** Enforces strict 4-way cardinal connectivity for rivers (`~`) to avoid diagonal water leaks and ensure sound downstream bridge and navigation topology.
   - **Validation Engine:** Automatically validates grid dimensions (strictly 32x32), verifies all characters in `region_grid` exist in the `regions` dictionary, guarantees region `'0'` is mapped to `"Unnamed Wilderness"`, and keeps `features` strictly empty for the primordial age.
   - **Visual CLI Preview:** Renders an ASCII map preview and regional registry breakdown directly to the terminal upon completion.
   - **Resilience & Tracking:** Employs exponential backoff retry handling and tracks token usage (prompt, candidate, thinking, and total counts).
