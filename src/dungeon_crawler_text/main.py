"""Main entry point for running the Cartographer & Historian world-building simulation."""

import argparse
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dungeon_crawler_text.cartographer import Cartographer
from dungeon_crawler_text.historian import Historian


def run_simulation(num_turns: int = 3, model_name: str = "gemini-3.6-flash") -> None:
    """Initializes Cartographer and Historian agents and runs their multi-turn collaboration."""
    load_dotenv()

    print("=" * 80, flush=True)
    print(" 🗺️  WORLD BUILDER SIMULATION: CARTOGRAPHER & HISTORIAN  📜", flush=True)
    print("=" * 80, flush=True)

    print(f"\nInitializing Cartographer agent ({model_name})...", flush=True)
    cartographer = Cartographer(model_name=model_name)

    print(f"Initializing Historian agent ({model_name})...", flush=True)
    historian = Historian(model_name=model_name)

    # Initial question from Cartographer
    query = cartographer.start_chronicle()

    for turn in range(1, num_turns + 1):
        print(f"\n{'='*35} TURN {turn} {'='*35}\n", flush=True)

        print("🧭 CARTOGRAPHER PROMPTS HISTORIAN:", flush=True)
        print(f'"{query}"\n', flush=True)

        print("📜 HISTORIAN NARRATES:", flush=True)
        narrative = historian.narrate(query)
        print(narrative, flush=True)
        print("\n" + "-" * 80 + "\n", flush=True)

        print("🗺️ CARTOGRAPHER UPDATES MAP & LOG:", flush=True)
        cartographer_response = cartographer.process_narrative(narrative)
        print(cartographer_response, flush=True)

        # Update query for next turn
        query = "What happened next in the chronicle of this land?"

    print("\n" + "=" * 80, flush=True)
    print(" ✅ WORLD BUILDING CHRONICLE SIMULATION COMPLETE", flush=True)
    print("=" * 80, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Cartographer and Historian agent interaction."
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=2,
        help="Number of historical turns to simulate (default: 2)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.6-flash",
        help="Gemini model to use (default: gemini-3.6-flash)",
    )

    args = parser.parse_args()

    try:
        run_simulation(num_turns=args.turns, model_name=args.model)
    except Exception as e:
        print(f"\n❌ Error running simulation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
