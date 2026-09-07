# Dungeon Crawler Text: Loremaster Primordial World-Building

A generative fantasy world-building tool powered by Gemini. The **Loremaster** agent describes the untouched, primordial landscape and raw geography of a fantasy realm at the dawn of time, balancing Tolkien-esque mythic depth with gritty, atmospheric weight.

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

## Running the Generator

Generate the primordial landscape via the package entry point:

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
| `--model` | `str` | `gemini-3.6-flash` | Gemini model to use for the agent |
| `--thinking` | `str` | `MEDIUM` | Thinking budget / level (`HIGH`, `MEDIUM`, `LOW`, etc.) |
| `--query` | `str` | *Default Primordial Query* | Custom prompt query to ask the Loremaster |
| `--output`, `-o` | `str` | `artifacts/worldprose.md` | File or directory path to save the output artifact file |

### Examples

- **Default run (saves to `artifacts/worldprose.md`):**
  ```bash
  uv run dungeon-crawler-text
  ```

- **Save landscape description to a custom path:**
  ```bash
  uv run dungeon-crawler-text --output custom_world.md
  ```

- **Use a custom query:**
  ```bash
  uv run dungeon-crawler-text --query "Describe a primordial volcanic island chain surrounded by boiling reefs."
  ```

---

## Architecture & How It Works

1. **System Prompt (`loremaster_worldprose.md`):**
   - Anchors the model in high-fantasy mythic world-building (Tolkien + Kentaro Miura).
   - Constrains the narrative to primordial physical geography: natural boundaries, mountain ridges, waterways, coastlines, and untamed biomes before mortal civilizations or settlements.

2. **Single-Question Generation (`Loremaster` & `main.py`):**
   - Dispatches a single focused query via `client.models.generate_content`.
   - Displays the narrative prose and tracks token usage.
   - Saves clean Markdown if an output path is provided.
