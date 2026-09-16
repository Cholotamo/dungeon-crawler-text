# Dungeon Crawler Text

A generative fantasy world-building pipeline powered by Gemini. It crafts living, mythic fantasy realms starting from dawn-of-time lore down to a concrete 32x32 cartographic world map and 16x16 local tactical maps.

## How to Clone and Run It

### Prerequisites
- **Python:** `>= 3.14` (as specified in `pyproject.toml`)
- **Package Manager:** [`uv`](https://github.com/astral-sh/uv)
- **Gemini API Key:** Set in a `.env` file in the project root

### Clone the Repository
```bash
git clone https://github.com/Cholotamo/dungeon-crawler-text.git
cd dungeon-crawler-text
```

### Setup Environment
Create a `.env` file and set up your Gemini API key:
```bash
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

Install dependencies and set up the virtual environment using `uv`:
```bash
uv sync
```

### Run the Pipeline
Generate the entire living fantasy world from scratch in a single command. This automates all stages from primordial world prose down to the 32x32 world map, historical epoch chronicle, landmark dossiers, seeds, vectors, concurrent 16x16 localemaps, and the interactive viewer.

```bash
uv run dungeon-crawler-pipeline
```
*(This will run the master pipeline with the default settings: 3 epochs, 4 concurrent workers, and output into the `artifacts/` folder.)*

You can also open the viewer automatically upon completion:
```bash
uv run dungeon-crawler-pipeline --open
```

Alternatively, you can manually run individual agents (e.g., `uv run dungeon-crawler-text` for the Loremaster, `uv run dungeon-crawler-historian` for the Historian).

To view the generated maps manually, simply open `viewer.html` or `artifacts/viewer.html` in your web browser.

---

## How It Works

The generative pipeline is orchestrated through a sequence of specialized AI agents and tools that run consecutively:

1. **Loremaster (`dungeon_crawler_text.main`)**
   - Synthesizes evocative, mythic narrative prose describing the untouched primordial landscape and raw physical geography of a realm at the dawn of creation.
   - Outputs: `artifacts/worldprose.md`

2. **Architect (`dungeon_crawler_text.architect`)**
   - Translates the primordial world prose into a structured 32x32 ASCII and JSON world map. 
   - Uses Gemini with **Python Code Execution** to enforce organic biome geography and strict hydrological rules.
   - Outputs: `artifacts/worldmap.json` and `artifacts/worldmap.md`

3. **Historian (`dungeon_crawler_text.historian`)**
   - Chronicles the passage of historical epochs.
   - Translates narrative developments into physical changes on the world map (founding settlements, paving roads, mutating regions) using fine-grained Feature CRUD Tools via Gemini Automatic Function Calling.
   - Outputs: `artifacts/worldmap_epoch_{n}.json` and `.md`

4. **Dossier Harvester (`dungeon_crawler_text.dossier`)**
   - Extracts deterministic spatial, geographic, and infrastructural vector dossiers across epochs for settlements, cities, and dungeons. 
   - Tracks keyframe mutations, local terrain/biome slices, and road/gate approaches.
   - Outputs: `artifacts/locales/{id}/dossier.json`

5. **Seed Synthesizer (`dungeon_crawler_text.seed`)**
   - Compiles vector dossiers into clean, prompt-ready Locale Generation Seeds.
   - Feeds downstream models with deterministic perimeter edge constraints, road access alignments, and scale footprints.
   - Outputs: `artifacts/locales/{id}/seed.md`

6. **Subarchitect (`dungeon_crawler_text.subarchitect`)**
   - Procedurally designs living **16x16 Tactical Locale Maps** from locale seeds using Gemini with **Python Code Execution**.
   - Generates zoned districts, physical architecture, perimeter-matching boundaries, and contextual feature overlays.
   - Outputs: `artifacts/locales/{id}/localemap_keyframe_0.json` and `.md`

7. **Subhistorian (`dungeon_crawler_text.subhistorian`)**
   - Algorithmically evolves the 16x16 localemaps across epochs from one keyframe to the next.
   - Uses sparse evolution vectors and Python code execution to preserve spatial continuity while applying historical mutations (e.g., expanding towns, ruining forts).
   - Outputs: `artifacts/locales/{id}/localemap_keyframe_{i+1}.json` and `.md`

### Visualization

- **Map Viewer (`viewer.html` / `build_viewer.py`)**: An interactive HTML Map Viewer to inspect the composite world map. It features a hover inspection HUD (revealing coordinates, terrain, biome, and feature lore), side-by-side view with region grids, and interactive legend filters.
