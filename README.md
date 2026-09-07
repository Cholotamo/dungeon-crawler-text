# Dungeon Crawler Text: Historian World-Building Simulation

A generative fantasy world-building simulation powered by Gemini. The **Historian** agent chronicles the rise, evolution, and transformation of a fantasy realm across epochs, maintaining continuous conversation memory and establishing chronological calendar reckonings.

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

Run the Historian narrative generation via the package entry point:

```bash
uv run dungeon-crawler-text
```

Alternatively, invoke the module directly with Python:

```bash
uv run python -m dungeon_crawler_text.main
```

---

## CLI Options

Customize the generation using command-line arguments:

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--epochs` / `--turns` | `int` | `2` | Number of historical epochs to simulate |
| `--model` | `str` | `gemini-3.7-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `HIGH` | Thinking budget / level (`HIGH`, `LOW`, etc.) |
| `--output-dir` | `str` | `None` | Optional directory where epoch Markdown files are saved |

### Examples

- **Generate 3 epochs:**
  ```bash
  uv run dungeon-crawler-text --epochs 3
  ```

- **Save chronicles to a directory:**
  ```bash
  uv run dungeon-crawler-text --epochs 3 --output-dir chronicles
  ```

---

## Architecture & How It Works

1. **Turn 1 (Primordial Creation):**
   - The Historian establishes the foundational landscape: natural boundaries, coasts, waterways, mountain ridges, and initial biomes.
   - Outputs a canonical Chronology block (reckoning system and elapsed time).

2. **Turn 2+ (Living Chronicle):**
   - Retaining chat history across epochs, the Historian advances the world's geopolitical and environmental narrative.
   - Chronicles civilization origins, territorial expansion, terraforming, catastrophes, and emergence of ruins and dungeons.
   - Extracts structured chronology metadata and clean narrative prose.
