# Dungeon Crawler Text: Primordial World-Building Pipeline

A generative fantasy world-building pipeline powered by Gemini. The pipeline operates in four coordinated stages to craft living, mythic fantasy realms from dawn-of-time lore down to a concrete 32x32 cartographic world map and rich landmark vector dossiers:

1. **The Loremaster:** Synthesizes evocative, mythic narrative prose describing the untouched primordial landscape and raw physical geography of a realm at the dawn of creation.
2. **The Architect:** Translates the primordial world prose into a structured 32x32 ASCII and JSON world map using Gemini with **Python Code Execution**, enforcing organic biome geography and strict hydrological rules.
3. **The Historian:** Chronicles the passage of historical epochs, translating narrative developments into physical changes on the map using fine-grained **Feature CRUD Tools** via Gemini Automatic Function Calling (AFC).
4. **The Dossier Harvester:** Extracts deterministic spatial, geographic, and infrastructural vector dossiers across epochs for settlements, cities, and dungeons, tracking keyframe mutations, local terrain/biome slices, and cardinal road/gate approaches for downstream subarchitect models.

```
                    ┌─────────────────────────┐
                    │   Primordial Prompt /   │
                    │          Query          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       Loremaster        │
                    │  (gemini-3.8-flash)     │
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
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Dossier Harvester    │
                    │  (Vector Extraction)    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ artifacts/dossiers/     │
                    │   {id}_dossier.json     │
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
| `--model` | `str` | `gemini-3.8-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `HIGH` | Thinking budget / level (`HIGH`, `MEDIUM`, `LOW`, etc.) |
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

### Step 3: Advance Epochs & Mutate Map Features & Region Lore (Historian)

Advance time across historical epochs, founding settlements, paving trade roads, building bridges, discovering ancient ruins, and mutating regional biomes and region lore as civilizations expand or fall, using the Historian agent equipped with **Feature CRUD, Semantic Terraforming, and Region Mutation tools**:

```bash
uv run dungeon-crawler-historian
```

Or invoke via Python module:

```bash
uv run python -m dungeon_crawler_text.historian
```

#### Historian Workflow
- **Turn 1 (Epoch 1):** Takes `artifacts/worldmap.md` as input, creates an active copy `artifacts/worldmap_epoch_1.json`, mutates features and regions via tools, and saves the rendered companion `artifacts/worldmap_epoch_1.md`.
- **Subsequent Turns (Epoch 2+):** Automatically takes the previous epoch markdown (`worldmap_epoch_1.md`) as input, creates `worldmap_epoch_2.json`, applies further mutations (upgrading settlements to cities `'O'`, paving roads `'+'`, creating dungeons `'!'`, expanding domains `:`, mutating region lore via `update_region`), and saves `worldmap_epoch_2.md`.

#### Historian CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input`, `-i` | `str` | *Auto-detect latest epoch* | Input markdown file path |
| `--epochs`, `-n` | `int` | `1` | Number of sequential epochs to advance within the same conversation |
| `--query`, `-q` | `str` | *Epoch Default* | Custom historical prompt or directive for the epoch |
| `--interactive` | `flag` | `False` | Run interactively, prompting for epoch directives within the same conversation |
| `--model` | `str` | `gemini-3.8-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `HIGH` | Thinking level for Gemini models (`HIGH`, `MEDIUM`, `LOW`) |
| `--max-afc-calls` | `int` | `20` | Maximum number of remote calls for automatic function calling (AFC) |

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

### Step 4: Harvest Landmark Vector Dossiers (Dossier Generator)

Extract deterministic spatial, geographic, and infrastructural vector dossiers for all settlements, cities, and dungeons across historical epochs (`worldmap_epoch_*.json`) to feed downstream Subarchitect generation models:

```bash
uv run dungeon-crawler-dossier
```

Or invoke the module directly:

```bash
uv run python -m dungeon_crawler_text.dossier
```

#### Dossier Harvester CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--feature`, `-f` | `str` | `""` (all landmarks) | Specific Feature ID to harvest (harvests all landmarks if omitted) |
| `--artifacts`, `-a` | `str` | `artifacts` | Directory containing epoch files (`worldmap_epoch_*.json`) |
| `--output`, `-o` | `str` | `artifacts/dossiers` | Output directory to save JSON dossier files |
| `--radius`, `-r` | `int` | `1` | Environmental scan radius (`1` yields 3x3 local slice, `2` yields 5x5) |

**Examples:**
```bash
# Harvest dossiers for all landmarks across all epochs into artifacts/dossiers/
uv run dungeon-crawler-dossier

# Harvest and inspect a specific landmark dossier (saves file & prints JSON to stdout)
uv run dungeon-crawler-dossier --feature eldermere

# Custom artifacts directory and output destination
uv run dungeon-crawler-dossier --artifacts artifacts --output custom_dossiers

# Expand environmental scan radius to 2 (5x5 neighborhood slice)
uv run dungeon-crawler-dossier --radius 2
```

#### What Dossier Vectors Contain

Each landmark dossier (`{feature_id}_dossier.json`) provides a complete, deterministic multi-epoch profile:
- **Spatial Positioning:** Fixed grid coordinates `[X, Y]`, founding epoch (`first_seen_epoch`), and latest active epoch.
- **Keyframe Evolution & Triggers:** Chronological snapshots flagged by state changes: `genesis`, `char_mutation` (e.g. outpost `'o'` -> city `'O'`), `name_mutation`, `domain_mutation` (host region shifts), `terrain_mutation`, and `new_roads`.
- **Local Environmental Context:** Local `(2r+1) x (2r+1)` ASCII terrain and region grid slices centered on the landmark, alongside host region lore and detected neighboring biomes with cardinal boundary positions (e.g., `"WEST BORDER (3 tiles)"`).
- **Infrastructural Network & Gate Approaches:** Connected roads (`+`) and bridges (`=`), including computed entry orientations (`NORTH`, `SOUTH`, `EAST`, `WEST`, `NORTH_EAST`, etc.) and linked destination landmarks.
- **Deterministic Delta Diffs:** Explicit transitions between keyframes (`biome_mutation`, `terrain_transition`, `status_transition`, and new road connections) for downstream procedural generation.

#### Dossier JSON Schema Excerpt

```json
{
  "feature_id": "eldermere",
  "world_coords": [25, 13],
  "first_seen_epoch": 1,
  "latest_epoch": 3,
  "total_keyframes": 3,
  "keyframes": [
    {
      "keyframe_index": 0,
      "epoch": 1,
      "char": "o",
      "name": "Eldermere",
      "type": "settlement",
      "is_keyframe": true,
      "keyframe_triggers": ["genesis"],
      "environment": {
        "host_region": {
          "id": "E",
          "name": "Eldermere Crofts",
          "type": "farmland",
          "lore": "Rich alluvial soil tilled by the pioneers of Eldermere along the eastern strand..."
        },
        "terrain_char": ":",
        "terrain_label": "farmland",
        "terrain_slice": [
          ";::",
          ";::",
          ";::"
        ],
        "region_slice": [
          "LEE",
          "LEE",
          "LEE"
        ],
        "neighborhood_regions": [
          {
            "id": "L",
            "name": "The Inland Sea",
            "type": "lake",
            "tile_count": 3,
            "relative_position": "WEST BORDER (3 tiles)",
            "lore": "A broad, cold, and bottomless freshwater sea...",
            "historical_context": "Active region in Epoch 1."
          }
        ]
      },
      "connected_roads": [
        {
          "road_id": "dawn_way",
          "road_name": "The Dawn Way",
          "road_type": "road",
          "gate_approach": "NORTH",
          "description": "An early beaten trade path...",
          "destination": {
            "feature_id": "gorgewatch",
            "name": "Gorgewatch",
            "type": "outpost"
          },
          "destination_coord": [22, 9]
        }
      ],
      "delta_from_previous": null
    }
  ]
}
```

---

### Step 5: Inspect Maps Interactively (HTML Map Viewer)

Open the interactive HTML Map Viewer to inspect the composite world map with rich colors, customizable tile spacing, and full hover inspection:

```bash
# Generate/update the viewer and open it directly in your default browser
uv run dungeon-crawler-viewer --open
```

Or open [`viewer.html`](file:///C:/Developer/Random/dungeon-crawler-text/viewer.html) or [`artifacts/viewer.html`](file:///C:/Developer/Random/dungeon-crawler-text/artifacts/viewer.html) directly in any browser.

#### Viewer Features:
- **Composite Map Rendering:** Accurately layers features (cities, outposts, dungeons, roads, bridges) over natural terrain following strict cartographic priority rules.
- **Hover Inspection HUD & Sidebar:** Hovering over any tile reveals:
  - **Tile Coordinates:** `[X, Y]` with highlighted crosshair rulers (00..31).
  - **Natural Terrain Ground:** Terrain character (e.g. `~`, `.`, `#`, `:`) and full type name/description.
  - **Regional Biome:** Region ID, Region Name, and Region Type.
  - **Feature Landmark:** Feature ID, Name, Type, Symbol, and comprehensive lore narrative.
- **Side-by-Side View:** Compare the Composite Map side-by-side with the Region Biomes Grid with synchronized cross-hover.
- **Visual Controls:** Sliders to adjust tile size (16px..44px) and spacing/gap (0px..6px), plus toggles for glyphs and coordinate axes.
- **Interactive Legend & Filters:** Click terrain types, regions, or features in the sidebar to highlight corresponding tiles across the realm.
- **Custom JSON Loading:** Switch between embedded historical epochs, drag-and-drop any custom `worldmap*.json` file, or paste raw JSON.

---

## Python API

All agents and harvesters can be imported and executed programmatically:

```python
from dungeon_crawler_text import (
    Architect,
    Historian,
    Loremaster,
    harvest_all_dossiers,
    harvest_landmark_keyframes,
)

# 1. Generate primordial narrative prose
loremaster = Loremaster(model_name="gemini-3.8-flash", thinking_level="HIGH")
prose = loremaster.generate_primordial_world()

# 2. Architect 32x32 world map from prose
architect = Architect(model_name="gemini-3.6-flash", thinking_level="MEDIUM")
world_map = architect.generate_world_map(worldprose=prose)
architect.save_world_map(world_map)

# 3. Advance world history across epochs using the Historian
historian = Historian(model_name="gemini-3.8-flash", thinking_level="HIGH")

# Run Epoch 1 (takes worldmap.md, creates worldmap_epoch_1.json and worldmap_epoch_1.md)
res_epoch1 = historian.run_epoch()

# Run Epoch 2 in the same conversation (takes worldmap_epoch_1.md, creates worldmap_epoch_2.json and worldmap_epoch_2.md)
res_epoch2 = historian.run_epoch()

# 4. Harvest deterministic vector dossiers across all epochs
all_dossiers = harvest_all_dossiers(
    artifacts_dir="artifacts",
    output_dir="artifacts/dossiers",
    scan_radius=1,
)

# Or extract a single landmark dossier
eldermere_dossier = harvest_landmark_keyframes(
    feature_id="eldermere",
    artifacts_dir="artifacts",
    scan_radius=1,
)
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
    "0": {
      "name": "Unnamed Wilderness",
      "type": "wilderness",
      "lore": "Untamed and primeval wilderness connecting the distinct geographic landmarks of the realm."
    },
    "1": {
      "name": "Iron-Grip Coast",
      "type": "coastal",
      "lore": "A storm-lashed shoreline of basalt sea stacks and churning dark surf."
    }
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

3. **Historian (`historian.py` & `prompts/historian_epoch.md`):**
   - **Chronological Epoch Simulation:** Advances the historical timeline across sequential epochs, simulating settlement founding, highway expansion, border shifts, and ruin discovery.
   - **Feature CRUD Tools:** Mutates features with Gemini Automatic Function Calling (AFC) tools (`add_feature`, `update_feature`, `delete_feature`, `update_region`, `terraform_tiles`).
   - **Multi-Epoch Context Window:** Retains world history across turns in continuous multi-epoch sessions, emitting updated JSON state and companion markdown maps.

4. **Dossier Harvester (`dossier.py`):**
   - **Multi-Epoch Vector Compilation:** Discovers all landmarks (settlements, cities, dungeons) in the latest epoch and parses the entire epoch history to extract deterministic temporal keyframes.
   - **Spatial & Infrastructural Extraction:** Extracts local terrain/biome ASCII slices, neighboring region boundaries, connected roads and bridges, and cardinal highway gate approaches (`NORTH`, `SOUTH`, etc.).
   - **Keyframe Mutation Tracking:** Identifies structural triggers (`genesis`, `char_mutation`, `domain_mutation`, `terrain_mutation`, `new_roads`) and computes deterministic deltas to feed downstream Subarchitect models.
