"""
This module contains the StoryWriter which is responsible for generating the world of the game.
"""

from collections.abc import Generator
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def save_artifact(category: str, filename: str, content: str) -> str:
    """Saves a markdown artifact file into the artifacts directory under the specified subfolder.

    Args:
        category: Subfolder category. Must be one of: 'quests', 'cities', 'dungeons', 'calendar', 'player'.
        filename: Name of the file (e.g., 'main_quest.md', 'stats.md').
        content: The markdown content to write into the file.

    Returns:
        A status message indicating success or failure.
    """
    valid_categories = {"quests", "cities", "dungeons", "calendar", "player"}
    cat = category.strip().lower()
    if cat not in valid_categories:
        return f"Error: '{category}' is not a valid category. Valid categories are: {', '.join(sorted(valid_categories))}."

    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    dir_path = Path("artifacts") / cat
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename

    try:
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully saved artifact to '{file_path.as_posix()}'."
    except Exception as e:
        return f"Failed to save artifact '{filename}': {e}"


system_prompt = """
You write dark fantasy stories for a text based dungeon crawling game. 

The writing tone is similar to Tolkien’s. However, you cannot copy anything else. 

The story should include at least one main quest, and multiple side quests that do not necessarily relate to the main quest. 

Your writing should allow for open-world exploration and not pressing the player towards the main quest early on. 

# Your Process
1. Before generating the world artifacts, ask the player a series of at most 5 player creation questions in a back and forth style.
2. Once the player creation process is complete, generate the complete world data and save each piece into .md files inside the `artifacts` directory using the `save_artifact` tool.

# Artifact Output Structure
Do NOT output the detailed game world files as standard chat responses to the player. Instead, use the `save_artifact` tool to write .md files into the following subfolders:

- `quests`:
  - Main history of the land and details/stages of the main quest (e.g. `main_quest.md`).
  - Details and required stages of each side quest (e.g. individual quest files `side_quest_1.md`, `side_quest_2.md`, etc.).
- `cities`:
  - 15 cities' names, geographical locations, histories, and quest involvements (e.g. individual city files `city_1.md`, `city_2.md`, etc.).
- `dungeons`:
  - 15 dungeons' names, geographical locations (wilderness or underground), histories, and quest involvements (e.g. individual dungeon files `dungeon_1.md`, `dungeon_2.md`, etc.).
- `calendar`:
  - The world's calendar system, time system, and date ranges for each season (e.g. `calendar.md`).
- `player`:
  - Player background history based on their answers (e.g. `history.md`).
  - Player stats (Strength, Intelligence, Endurance, Faith, Luck: each 0-100, biased under 40) (e.g. `stats.md`).

When saving files with `save_artifact`, provide:
- `category`: one of 'quests', 'cities', 'dungeons', 'calendar', or 'player'
- `filename`: the destination file name (e.g. 'main_quest.md')
- `content`: the complete markdown content for that section.
"""


class StoryWriter:
    """Manages the chat session with Gemini for story & world generation."""

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
                system_instruction=system_prompt,
                temperature=0.7,
                tools=[save_artifact],
            ),
        )


    def start_chat(
        self,
        initial_prompt: str = "Greetings Story Writer. Please introduce yourself briefly and ask the first player creation question.",
    ) -> str:
        """Start the back-and-forth session with an initial prompt."""
        response = self.chat.send_message(initial_prompt)
        return response.text or ""

    def send_message(self, message: str) -> str:
        """Send a player response or question to the StoryWriter."""
        response = self.chat.send_message(message)
        return response.text or ""

    def send_message_stream(self, message: str) -> Generator[str, None, None]:
        """Send a message to the StoryWriter and yield streaming text response chunks."""
        response = self.chat.send_message_stream(message)
        for chunk in response:
            if chunk.text:
                yield chunk.text


def run_interactive_session(model: str = "gemini-3.6-flash") -> None:
    """
    Runs an interactive back-and-forth terminal chat loop with the StoryWriter.
    The StoryWriter asks player creation questions before generating the world details.
    """
    print("=" * 60)
    print("  Dungeon Crawler - StoryWriter Character & World Creation")
    print("=" * 60)
    print("Type 'exit' or 'quit' to terminate the session.\n")

    writer = StoryWriter(model=model)

    initial_prompt = (
        "Greetings Story Writer. Please introduce yourself briefly and ask the first player creation question."
    )
    print("StoryWriter: ", end="", flush=True)
    try:
        for chunk in writer.send_message_stream(initial_prompt):
            print(chunk, end="", flush=True)
        print("\n")
    except Exception as err:
        print(f"\n[Error connecting to Gemini API: {err}]")
        print("Please verify that GEMINI_API_KEY environment variable is set.")
        return

    while True:
        try:
            user_input = input("Player > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Ending story writer chat session.")
            break

        print("\nStoryWriter: ", end="", flush=True)
        try:
            for chunk in writer.send_message_stream(user_input):
                print(chunk, end="", flush=True)
            print("\n")
        except Exception as err:
            print(f"\n[Error during conversation: {err}]")
            break


if __name__ == "__main__":
    run_interactive_session()


