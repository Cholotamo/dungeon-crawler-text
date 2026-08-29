"""
This module contains the StoryWriter which is responsible for generating the world of the game.
"""

from collections.abc import Generator
import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


system_prompt = """
You write dark fantasy stories for a text based dungeon crawling game. 

The writing tone is similar to Tolkien’s. However, you cannot copy anything else. 

The story should include at least one main quest, and multiple side quests that do not necessarily relate to the main quest. 

Your writing should allow for open-world exploration and not pressing the player towards the main quest early on. 

# Generation
You are to generate:
1. The name and history of the country
2. 15 cities’ names, geographical locations, and histories within the country
3. 15 dungeons’ names, geographical locations, and histories in the wilderness of the country. Dungeons need not be underground, as long as they are places where the player can find danger. 
4. The world’s calendar, including the ranges of dates for each season
5. The player’s history, and stats
  - To generate the player, ask them a series of at most 5 questions. The questions must be asked in a back and forth style. 

# Output
The output is not for the player. It is supposed to be sent to an agent that will carry the player through the story, so be as detailed as possible for the quest actions. 
You are to follow this style of output:

## Overarching story
Here you will write the main history of the land and the details of the main quest. 

## Quest details
Here you will write the details and required stages of each quest and how they can be progressed. For each quest, think about relevant locations and objectives. 

## Geography - Civilization
Here you will write the list of cities and their histories. If the city is involved in a quest, state its involvement here. 

## Geography - Dungeons
Here you will write the list of dungeons and their histories. If the dungeon is involved in a quest, state its involvement here. 

## Calendar
Here you will write the time system the world uses, and the current season it is

## Player - History
Here you will write the background of the player 

## Player - Stats
Each stat is a number from 0-100, biased to be under 40.
- Strength
- Intelligence
- Endurance
- Faith
- Luck

# Your process
Before outputting anything to the player, ask them their player creation questions first.
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


