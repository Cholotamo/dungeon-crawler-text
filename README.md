# Dungeon Crawler Text: Primordial World-Building Pipeline

A generative fantasy world-building pipeline powered by Gemini. The pipeline operates in six coordinated stages to craft living, mythic fantasy realms from dawn-of-time lore down to a concrete 32x32 cartographic world map, rich landmark vector dossiers, deterministic locale generation seeds, and tactical 16x16 localemaps:

1. **The Loremaster:** Synthesizes evocative, mythic narrative prose describing the untouched primordial landscape and raw physical geography of a realm at the dawn of creation.
2. **The Architect:** Translates the primordial world prose into a structured 32x32 ASCII and JSON world map using Gemini with **Python Code Execution**, enforcing organic biome geography and strict hydrological rules.
3. **The Historian:** Chronicles the passage of historical epochs, translating narrative developments into physical changes on the map using fine-grained **Feature CRUD Tools** via Gemini Automatic Function Calling (AFC).
4. **The Dossier Harvester:** Extracts deterministic spatial, geographic, and infrastructural vector dossiers across epochs for settlements, cities, and dungeons, tracking keyframe mutations, local terrain/biome slices, and cardinal road/gate approaches.
5. **The Seed Synthesizer:** Compiles vector dossiers into clean, prompt-ready **Locale Generation Seeds** (`{id}_epoch_{n}_seed.md`), feeding downstream Subarchitect models with deterministic perimeter edge constraints, road access alignments, and scale footprints.
6. **The Subarchitect:** Procedurally designs living **16x16 Tactical Locale Maps** (`localemap_keyframe_{n}.json`) from locale seeds using Gemini with **Python Code Execution**, generating zoned districts, physical architecture, perimeter-matching boundaries, and contextual feature overlays.

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
                    │ artifacts/locales/{id}/ │
                    │   dossier.json          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     Seed Synthesizer    │
                    │   (Locale Seeds)        │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ artifacts/locales/{id}/ │
                    │   seed.md               │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      Subarchitect       │
                    │ (LLM + Code Execution)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ artifacts/locales/{id}/ │
                    │   localemap_keyframe_0  │
                    │   (.json and .md)       │
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
| `--output`, `-o` | `str` | `artifacts/locales` | Output directory to save locale dossiers |
| `--radius`, `-r` | `int` | `1` | Environmental scan radius (`1` yields 3x3 local slice, `2` yields 5x5) |

**Examples:**
```bash
# Harvest dossiers for all landmarks across all epochs into artifacts/locales/{id}/dossier.json
uv run dungeon-crawler-dossier

# Harvest and inspect a specific landmark dossier (saves file & prints JSON to stdout)
uv run dungeon-crawler-dossier --feature eldermere

# Custom artifacts directory and output destination
uv run dungeon-crawler-dossier --artifacts artifacts --output custom_locales

# Expand environmental scan radius to 2 (5x5 neighborhood slice)
uv run dungeon-crawler-dossier --radius 2
```

#### What Dossier Vectors Contain

Each landmark dossier (`artifacts/locales/{feature_id}/dossier.json`) provides a complete, deterministic multi-epoch profile:
- **Spatial Positioning:** Fixed grid coordinates `[X, Y]`, founding epoch (`first_seen_epoch`), and latest active epoch.
- **Landmark Identity & Lore:** Epoch-specific names, character glyphs, landmark types, and narrative descriptions (`description`).
- **Keyframe Evolution & Triggers:** Chronological milestones flagged by state changes: `genesis`, `char_mutation` (e.g. outpost `'o'` -> city `'O'`), `name_mutation`, `domain_mutation` (host region shifts), `terrain_mutation`, and `new_roads`. Stagnant epochs without changes are omitted so every keyframe represents a genuine historical milestone.
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
      "description": "The first mortal haven founded on the eastern strand of the Inland Sea...",
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

### Step 5: Synthesize Locale Generation Seeds (Seed Generator)

Translate landmark vector dossiers into deterministic, context-driven **Locale Generation Seeds** (`artifacts/locales/{feature_id}/seed.md`) to guide the downstream Subarchitect model without distracting world coordinates or premature tile legends:

```bash
uv run dungeon-crawler-seed
```

Or invoke the module directly:

```bash
uv run python -m dungeon_crawler_text.seed
```

#### Seed Generator CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--feature`, `-f` | `str` | `""` (all landmarks) | Specific Feature ID to synthesize seed for |
| `--dossiers`, `-d` | `str` | `artifacts/locales` | Directory containing locale dossier folders |
| `--output`, `-o` | `str` | `artifacts/locales` | Output directory to save `seed.md` into each locale folder |
| `--keyframe`, `-k` | `int` | `0` | Keyframe index to extract (`0` = founding epoch / genesis) |

**Examples:**
```bash
# Synthesize seeds for all landmarks into artifacts/locales/{id}/seed.md
uv run dungeon-crawler-seed

# Synthesize and inspect a specific landmark seed
uv run dungeon-crawler-seed --feature eldenmere

# Synthesize for a later epoch keyframe (e.g. keyframe 1)
uv run dungeon-crawler-seed --feature eldenmere --keyframe 1
```

---

### Step 6: Procedurally Generate 16x16 Locale Maps (Subarchitect)

Translate deterministic Locale Generation Seeds (`artifacts/locales/{feature_id}/seed.md`) into fully realized, living **16x16 Tactical Locale Maps** (`localemap_keyframe_{n}.json` and companion `localemap_keyframe_{n}.md`) using the Subarchitect powered by Gemini with **Python Code Execution**:

```bash
uv run dungeon-crawler-subarchitect --locale eldenmere
```

Or invoke the module directly:

```bash
uv run python -m dungeon_crawler_text.subarchitect --locale eldenmere
```

#### Subarchitect Features & Workflow
- **Python Code Execution:** The Subarchitect writes and executes procedural Python code to sculpt naturalistic room layouts, palisades, roads, and waterways.
- **Dual-Grid System:** Generates both a physical `terrain_grid` (floors, walls, doors, roads, bridges, waters) and a zoning `district_grid` (wards, quarters, enclosures, or dungeon sectors).
- **Perimeter Edge Matching:** Enforces strict boundary continuity with the surrounding world map biomes identified in Section 3 of `seed.md`.
- **Road/Gate Alignment:** Connects inbound highway routes (`+`) and spans (`=`) at the exact cardinal boundary tiles specified in the seed's ingress requirements.
- **Contextual POI Feature Registry:** Populates interior buildings, gates, taverns, shrines, and keeps with exact tile coordinates, glyphs, and local lore.

#### Subarchitect CLI Options

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--locale`, `-f`, `--feature` | `str` | `""` | Feature ID to generate (searches `artifacts/locales/<id>/seed.md`) |
| `--seed`, `-s`, `-i`, `--input` | `str` | `""` | Path directly to a specific `seed.md` file |
| `--all`, `-a` | `flag` | `False` | Batch generate localemaps for all seeds found in `artifacts/locales` |
| `--keyframe`, `-k` | `int` | `0` | Keyframe index to generate (`0` = founding epoch / genesis) |
| `--epoch` | `int` | `None` | Historical epoch (auto-detected from dossier or seed if omitted) |
| `--output`, `-o` | `str` | `""` | Custom output file or directory path |
| `--model` | `str` | `gemini-3.6-flash` | Gemini model to use for code execution |
| `--thinking` | `str` | `MEDIUM` | Thinking level (`LOW`, `MEDIUM`, `HIGH`) |

**Examples:**
```bash
# Generate localemap for a specific locale (saves to artifacts/locales/eldenmere/localemap_keyframe_0.*)
uv run dungeon-crawler-subarchitect --locale eldenmere

# Generate from a direct seed file path
uv run dungeon-crawler-subarchitect --seed artifacts/locales/kraghollow/seed.md

# Batch generate localemaps for all available locales
uv run dungeon-crawler-subarchitect --all

# Generate for a specific historical epoch keyframe
uv run dungeon-crawler-subarchitect --locale eldenmere --keyframe 1

# Run with higher thinking budget or alternative model
uv run dungeon-crawler-subarchitect --locale eldenmere --model gemini-3.8-flash --thinking HIGH
```

---

### Step 7: Inspect Maps Interactively (HTML Map Viewer)

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

All agents, harvesters, and generators can be imported and executed programmatically:

```python
from pathlib import Path
from dungeon_crawler_text import (
    Architect,
    Historian,
    Loremaster,
    Subarchitect,
    harvest_all_dossiers,
    harvest_landmark_keyframes,
    generate_all_locale_seeds,
    generate_locale_seed,
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

# 4. Harvest deterministic vector dossiers across all epochs into artifacts/locales/{id}/dossier.json
all_dossiers = harvest_all_dossiers(
    artifacts_dir="artifacts",
    output_dir="artifacts/locales",
    scan_radius=1,
)

# 5. Synthesize deterministic locale generation seeds into artifacts/locales/{id}/seed.md
all_seeds = generate_all_locale_seeds(
    dossiers_dir="artifacts/locales",
    output_dir="artifacts/locales",
    keyframe_index=0,
)

# 6. Procedurally generate 16x16 localemaps using the Subarchitect
subarchitect = Subarchitect(model_name="gemini-3.6-flash", thinking_level="MEDIUM")
seed_text = Path("artifacts/locales/eldenmere/seed.md").read_text(encoding="utf-8")

locale_map = subarchitect.generate_localemap(
    seed_text=seed_text,
    keyframe_index=0,
    epoch=1,
)
json_path, md_path = subarchitect.save_localemap(
    locale_map,
    base_dir="artifacts/locales/eldenmere",
)
```

---

## Map Structure & Legends

### 1. World Map (32x32)

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

#### World Map Terrain Legend

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

### 2. Local Tactical Map (16x16)

The Subarchitect outputs a structured JSON artifact conforming to the following schema:

```json
{
  "name": "Eldenmere",
  "feature_id": "eldenmere",
  "type": "settlement",
  "keyframe_index": 0,
  "epoch": 1,
  "scale_category": "Small / Compact",
  "dimensions": [16, 16],
  "terrain_grid": [
    "16 strings of exactly 16 terrain chars..."
  ],
  "district_grid": [
    "16 strings of exactly 16 single-character district IDs..."
  ],
  "districts": {
    "0": {
      "name": "Frontier Outskirts",
      "type": "wilderness",
      "lore": "The untamed perimeter encircling the settlement."
    },
    "1": {
      "name": "Common Ward",
      "type": "residential",
      "lore": "Rustic timber steadings clustered around the dawn highway."
    }
  },
  "features": {
    "town_hall": {
      "name": "Town Hall",
      "type": "civic",
      "char": "H",
      "tiles": [[8, 8]],
      "lore": "The rustic governing lodge of Eldenmere."
    }
  }
}
```

#### Local Tactical Map Terrain Legend

| Char | Tactical Terrain Type | Description |
| :---: | :--- | :--- |
| `.` | Floor / Open Dirt | Open clearings, bare dirt, flagstone paving, or chamber floor |
| `,` | Turf / Grass / Moss | Untamed grass, mossy hummocks, lichen, or wild turf |
| `:` | Farmland / Scree | Tilled plots, garden beds, rubble, debris, or gravel yards |
| `~` | Deep Water | Navigable watercourse, mill pond, deep lake, or flooded cistern |
| `;` | Shallows / Shoreline | Mudflats, reed beds, tidal reaches, shallows, or flooded flags |
| `&` | Overgrowth / Thicket | Hedgerows, dense brambles, fungal clusters, or tangled brush |
| `^` | Elevated Stone / Ridge | Rocky outcrop, natural limestone bluff, chasm edge, or talus slope |
| `+` | Road / Corridor | Cobbled lane, thoroughfare, dirt highway, hallway, or passage |
| `=` | Span / Bridge | Timber bridge, stone culvert, pier, pontoon, or boardwalk |
| `#` | Solid Wall / Palisade | Hewn rock, masonry wall, timber palisade, or unworked stone |
| `/` | Ingress / Gate / Door | Gatehouse archway, heavy oak door, cavern mouth, or sally port |
| `|` | Partition / Fence | Wattle fence, paddock hurdle, low iron grate, or portcullis |

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

5. **Seed Synthesizer (`seed.py`):**
   - **Deterministic Seed Compilation:** Synthesizes clean, prompt-ready markdown seeds (`seed.md`) from multi-epoch landmark dossiers.
   - **Context-Pure Extraction:** Translates landmark scale profiles, perimeter border boundaries, and cardinal road ingress approaches into natural directives without leaking global coordinates or premature tile legends.

6. **Subarchitect (`subarchitect.py` & `prompts/subarchitect_localemap.md`):**
   - **Python Code Execution:** Operates with Gemini Python code execution enabled to procedurally synthesize organic, non-uniform 16x16 tactical maps from seeds.
   - **Dual-Grid Architecture:** Concurrently builds a base physical `terrain_grid` (walls, floors, doors, paths, waters) and a functional `district_grid` (wards, quarters, courtyards).
   - **Boundary & Road Alignment:** Validates that external perimeter edges match the surrounding biomes from the seed, and that highway roads/spans (`+`, `=`) enter at the exact assigned border positions.
   - **POI Feature Placement:** Populates interior points of interest (taverns, smithies, shrines, crypts, gates) with coordinate footprints, glyphs, and rich localized lore.
   - **Rigorous Grid Validation:** Defensively checks 16x16 dimensions, character sets, road connectivity, district assignments, and feature boundaries.
