"""
This module contains the StoryWriter which is responsible for generating the world of the game.
"""

from collections.abc import Generator
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()


class CityItem(BaseModel):
    name: str = Field(description="City name")
    location: str = Field(description="Geographical location within the country")
    history: str = Field(description="Detailed history of the city and any quest involvement")


class DungeonItem(BaseModel):
    name: str = Field(description="Dungeon name")
    location: str = Field(description="Geographical location in wilderness or underground")
    history: str = Field(description="Detailed history of dungeon, hazards, and quest involvement")


class QuestItem(BaseModel):
    title: str = Field(description="Quest title")
    summary: str = Field(description="Quest summary and narrative objective")
    stages: list[str] = Field(description="Required stages and steps to progress the quest")
    locations_involved: list[str] = Field(default=[], description="Names of cities or dungeons involved in this quest")


class MonthConfig(BaseModel):
    name: str = Field(description="Name of the month")
    days: int = Field(description="Number of days in the month", ge=1)
    season: str = Field(description="Associated season name")


class SeasonConfig(BaseModel):
    temperature: str = Field(description="Temperature description (e.g., Sub-zero Freezing, Mild)")
    weather_tendencies: list[str] = Field(description="List of weather tendencies (e.g., Snow, Fog)")
    description: str = Field(description="Season lore and climate description")


class HolidayConfig(BaseModel):
    name: str = Field(description="Holiday name")
    month: str = Field(description="Month of the holiday")
    day: int = Field(description="Day of the month (1-indexed)", ge=1)
    lore: str = Field(description="Lore and celebration details")


class MarkedEvent(BaseModel):
    id: str = Field(description="Unique event identifier")
    name: str = Field(description="Event name")
    description: str = Field(description="Event description, triggers, or consequences")
    trigger_hour: int = Field(description="Absolute elapsed hour when event triggers", ge=0)


def save_artifact(category: str, filename: str, content: str) -> str:
    """Saves an artifact file (.md or .json) into the artifacts directory under the specified subfolder.

    Args:
        category: Subfolder category. Must be one of: 'quests', 'cities', 'dungeons', 'calendar', 'player'.
        filename: Name of the file (e.g., 'main_quest.md', 'calendar.md').
        content: The markdown or text content string to write into the file.

    Returns:
        A status message indicating success or failure.
    """
    valid_categories = {"quests", "cities", "dungeons", "calendar", "player"}
    cat = category.strip().lower()
    if cat not in valid_categories:
        return f"Error: '{category}' is not a valid category. Valid categories are: {', '.join(sorted(valid_categories))}."

    # Default to .md if no file extension is provided
    if "." not in Path(filename).name:
        filename = f"{filename}.md"

    dir_path = Path("artifacts") / cat
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename

    try:
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully saved artifact to '{file_path.as_posix()}'."
    except Exception as e:
        return f"Failed to save artifact '{filename}': {e}"


def save_cities(cities: list[CityItem]) -> str:
    """Saves all 15 generated cities into individual files in 'artifacts/cities/'."""
    dir_path = Path("artifacts/cities")
    dir_path.mkdir(parents=True, exist_ok=True)
    saved_files = []
    for idx, city in enumerate(cities, 1):
        slug = city.name.lower().replace(" ", "_").replace("'", "")
        filename = f"city_{idx}_{slug}.md"
        content = f"# {city.name}\n\n**Location:** {city.location}\n\n## History & Lore\n{city.history}\n"
        file_path = dir_path / filename
        file_path.write_text(content, encoding="utf-8")
        saved_files.append(filename)
    return f"Successfully saved {len(saved_files)} cities into 'artifacts/cities/'."


def save_dungeons(dungeons: list[DungeonItem]) -> str:
    """Saves all 15 generated dungeons into individual files in 'artifacts/dungeons/'."""
    dir_path = Path("artifacts/dungeons")
    dir_path.mkdir(parents=True, exist_ok=True)
    saved_files = []
    for idx, dung in enumerate(dungeons, 1):
        slug = dung.name.lower().replace(" ", "_").replace("'", "")
        filename = f"dungeon_{idx}_{slug}.md"
        content = f"# {dung.name}\n\n**Location:** {dung.location}\n\n## History & Dangers\n{dung.history}\n"
        file_path = dir_path / filename
        file_path.write_text(content, encoding="utf-8")
        saved_files.append(filename)
    return f"Successfully saved {len(saved_files)} dungeons into 'artifacts/dungeons/'."


def save_quests(main_quest: QuestItem, side_quests: list[QuestItem]) -> str:
    """Saves main quest and side quests into individual markdown files in 'artifacts/quests/'."""
    dir_path = Path("artifacts/quests")
    dir_path.mkdir(parents=True, exist_ok=True)

    main_stages = "\n".join(f"{i}. {stage}" for i, stage in enumerate(main_quest.stages, 1))
    main_locs = ", ".join(main_quest.locations_involved) if main_quest.locations_involved else "Various"
    main_content = (
        f"# Main Quest: {main_quest.title}\n\n"
        f"**Summary:** {main_quest.summary}\n\n"
        f"**Locations Involved:** {main_locs}\n\n"
        f"## Quest Stages\n{main_stages}\n"
    )
    (dir_path / "main_quest.md").write_text(main_content, encoding="utf-8")

    saved_count = 1
    for idx, sq in enumerate(side_quests, 1):
        sq_stages = "\n".join(f"{i}. {stage}" for i, stage in enumerate(sq.stages, 1))
        sq_locs = ", ".join(sq.locations_involved) if sq.locations_involved else "Various"
        sq_content = (
            f"# Side Quest: {sq.title}\n\n"
            f"**Summary:** {sq.summary}\n\n"
            f"**Locations Involved:** {sq_locs}\n\n"
            f"## Quest Stages\n{sq_stages}\n"
        )
        (dir_path / f"side_quest_{idx}.md").write_text(sq_content, encoding="utf-8")
        saved_count += 1

    return f"Successfully saved {saved_count} quest files into 'artifacts/quests/'."


def save_player_profile(history: str, stats: dict[str, int]) -> str:
    """Saves player history and player stats to 'artifacts/player/history.md' and 'artifacts/player/stats.md'."""
    dir_path = Path("artifacts/player")
    dir_path.mkdir(parents=True, exist_ok=True)

    (dir_path / "history.md").write_text(f"# Player History\n\n{history}\n", encoding="utf-8")

    stats_lines = "\n".join(f"- **{k.capitalize()}**: {v}" for k, v in stats.items())
    (dir_path / "stats.md").write_text(f"# Player Stats\n\n{stats_lines}\n", encoding="utf-8")

    return "Successfully saved player history and stats into 'artifacts/player/'."


def save_time_config(
    hours_per_day: int,
    weekdays: list[str],
    months: list[MonthConfig],
    seasons: dict[str, SeasonConfig],
    holidays: list[HolidayConfig],
) -> str:
    """Generates and saves the static calendar configuration (FantasyTimeConfig) to 'artifacts/calendar/time_config.json'."""
    data = {
        "hours_per_day": hours_per_day,
        "weekdays": weekdays,
        "months": [m.model_dump() for m in months],
        "seasons": {k: v.model_dump() for k, v in seasons.items()},
        "holidays": [h.model_dump() for h in holidays],
    }
    dir_path = Path("artifacts/calendar")
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "time_config.json"
    try:
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return f"Successfully saved time config JSON to '{file_path.as_posix()}'."
    except Exception as e:
        return f"Failed to save time_config.json: {e}"


def save_time_state(
    total_hours: int,
    marked_events: list[MarkedEvent],
) -> str:
    """Generates and saves the initial runtime game time state (FantasyTimeState) to 'artifacts/calendar/time_state.json'."""
    data = {
        "total_hours": total_hours,
        "marked_events": [e.model_dump() for e in marked_events],
    }
    dir_path = Path("artifacts/calendar")
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "time_state.json"
    try:
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return f"Successfully saved time state JSON to '{file_path.as_posix()}'."
    except Exception as e:
        return f"Failed to save time_state.json: {e}"


def convert_time_state(time_state: dict, time_config: dict) -> dict:
    """Translates FantasyTimeState (total_hours & marked_events) into structured time

    (year, month, day, weekday, hour, season info, active holidays, and triggered events)
    using FantasyTimeConfig definitions.
    """
    total_hours = time_state.get("total_hours", 0)
    hours_per_day = time_config.get("hours_per_day", 24)
    weekdays = time_config.get("weekdays", ["Day 1"])
    months = time_config.get("months", [])
    seasons = time_config.get("seasons", {})
    holidays = time_config.get("holidays", [])
    marked_events = time_state.get("marked_events", [])

    total_days = total_hours // hours_per_day
    hour_of_day = total_hours % hours_per_day

    weekday_name = weekdays[total_days % len(weekdays)] if weekdays else "Unknown"

    year_length_days = sum(m.get("days", 1) for m in months) if months else 1
    year = (total_days // year_length_days) + 1
    day_in_year = total_days % year_length_days

    current_month_name = "Unknown"
    current_day_of_month = 1
    current_season_name = "Unknown"

    remaining_days = day_in_year
    for m in months:
        m_days = m.get("days", 1)
        if remaining_days < m_days:
            current_month_name = m.get("name", "Unknown")
            current_day_of_month = remaining_days + 1
            current_season_name = m.get("season", "Unknown")
            break
        remaining_days -= m_days

    season_info = seasons.get(current_season_name, {})

    active_holidays = [
        h for h in holidays
        if h.get("month") == current_month_name and h.get("day") == current_day_of_month
    ]

    triggered_events = [e for e in marked_events if e.get("trigger_hour", 0) <= total_hours]
    upcoming_events = [e for e in marked_events if e.get("trigger_hour", 0) > total_hours]

    return {
        "total_hours": total_hours,
        "year": year,
        "month": current_month_name,
        "day_of_month": current_day_of_month,
        "weekday": weekday_name,
        "hour_of_day": hour_of_day,
        "season": {
            "name": current_season_name,
            "temperature": season_info.get("temperature", ""),
            "weather_tendencies": season_info.get("weather_tendencies", []),
            "description": season_info.get("description", ""),
        },
        "active_holidays": active_holidays,
        "triggered_events": triggered_events,
        "upcoming_events": upcoming_events,
    }


def load_and_convert_calendar(artifacts_dir: str | Path = "artifacts") -> dict:
    """Loads time_state.json and time_config.json from artifacts/calendar/ and converts them to structured time."""
    calendar_dir = Path(artifacts_dir) / "calendar"
    state_file = calendar_dir / "time_state.json"
    config_file = calendar_dir / "time_config.json"

    if not state_file.exists() or not config_file.exists():
        raise FileNotFoundError(f"Missing calendar JSON files in '{calendar_dir.as_posix()}'")

    time_state = json.loads(state_file.read_text(encoding="utf-8"))
    time_config = json.loads(config_file.read_text(encoding="utf-8"))

    return convert_time_state(time_state, time_config)


system_prompt = """
You write dark fantasy stories for a text based dungeon crawling game. 

The writing tone is similar to Tolkien’s. However, you cannot copy anything else. 

The story should include at least one main quest, and multiple side quests that do not necessarily relate to the main quest. 

Your writing should allow for open-world exploration and not pressing the player towards the main quest early on. 

# Your Process
1. Before generating the world artifacts, ask the player a series of at most 5 player creation questions in a back and forth style.
2. Once the player creation process is complete, generate the complete world data using the dedicated batch tools.
3. MANDATORY FINAL STEP: Immediately after invoking the tools to generate all world artifacts, you MUST reply with a final spoken chat message directly to the player. Give them a brief, atmospheric overview and flavour text welcoming them into the realm. Do NOT reveal any secret quest details, story plots, or game mechanics. Never output an empty text message.

# Artifact Output Structure
Do NOT output raw artifact contents (such as JSON strings or entire Markdown documents) directly as chat text to the player. Instead, call the batch tools:

- `cities`: Use `save_cities` to save all 15 cities (names, locations, histories) into `artifacts/cities/`.
- `dungeons`: Use `save_dungeons` to save all 15 dungeons (names, locations, histories) into `artifacts/dungeons/`.
- `quests`: Use `save_quests` to save main quest and side quests into `artifacts/quests/`.
- `calendar`:
  - Call `save_time_config` tool to generate and save `artifacts/calendar/time_config.json`.
  - Call `save_time_state` tool to generate and save `artifacts/calendar/time_state.json`.
  - Use `save_artifact` tool to write calendar lore into `calendar/calendar.md`.
- `player`: Use `save_player_profile` to save player history (`history.md`) and stats (`stats.md`, numbers 0-100, biased under 40).
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
                max_output_tokens=8192,
                tools=[
                    save_artifact,
                    save_cities,
                    save_dungeons,
                    save_quests,
                    save_player_profile,
                    save_time_config,
                    save_time_state,
                ],
            ),
        )




    @staticmethod
    def _extract_text(response) -> str:
        if not response or not response.candidates:
            return ""
        texts = []
        for part in response.candidates[0].content.parts or []:
            if part.text:
                texts.append(part.text)
        return "".join(texts)

    def start_chat(
        self,
        initial_prompt: str = "Greetings Story Writer. Please introduce yourself briefly and ask the first player creation question.",
    ) -> str:
        """Start the back-and-forth session with an initial prompt."""
        response = self.chat.send_message(initial_prompt)
        return self._extract_text(response)

    def send_message(self, message: str) -> str:
        """Send a player response or question to the StoryWriter."""
        response = self.chat.send_message(message)
        return self._extract_text(response)

    def get_latest_response_text(self) -> str:
        """Returns the text content of the latest assistant message in chat history."""
        history = self.chat.get_history()
        if not history:
            return ""
        last_msg = history[-1]
        if getattr(last_msg, "role", "") != "model":
            return ""
        texts = []
        for part in getattr(last_msg, "parts", []) or []:
            if getattr(part, "text", None):
                texts.append(part.text)
        return "".join(texts)

    def send_message_stream(self, message: str) -> Generator[str, None, None]:
        """Send a message to the StoryWriter and yield streaming text response chunks."""
        response = self.chat.send_message_stream(message)
        yielded_any = False
        for chunk in response:
            if not chunk.candidates:
                continue
            for part in chunk.candidates[0].content.parts or []:
                if part.text:
                    yielded_any = True
                    yield part.text
        if not yielded_any:
            latest_text = self.get_latest_response_text()
            if latest_text:
                yield latest_text




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

        print("\nStory Writer: ", end="", flush=True)
        try:
            for chunk in writer.send_message_stream(user_input):
                print(chunk, end="", flush=True)
            print("\n")
        except Exception as err:
            print(f"\n[Error during conversation: {err}]")
            break


if __name__ == "__main__":
    run_interactive_session()


