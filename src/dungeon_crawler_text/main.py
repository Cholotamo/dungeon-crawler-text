"""Main entry point for running the Cartographer & Historian world-building simulation."""

import argparse
from pathlib import Path
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dungeon_crawler_text.cartographer import Cartographer
from dungeon_crawler_text.historian import Historian
from dungeon_crawler_text.world_state import WorldStateManager


def run_simulation(
    num_turns: int = 3,
    model_name: str = "gemini-3.7-flash",
    thinking_level: str = "HIGH",
    storage_dir: str = "artifacts/world_state",
) -> None:
    """Initializes Cartographer and Historian agents and runs their multi-turn collaboration

    grounded in persistent world state snapshots.
    """
    load_dotenv()

    world_dir = Path(storage_dir)
    print("=" * 80, flush=True)
    print(" 🗺️  WORLD BUILDER SIMULATION: CARTOGRAPHER & HISTORIAN  📜", flush=True)
    print(f" 💾 Persistent State Storage: {world_dir.resolve()}", flush=True)
    print("=" * 80, flush=True)

    state_manager = WorldStateManager(world_dir)

    print(f"\nInitializing Cartographer agent ({model_name}, thinking={thinking_level})...", flush=True)
    cartographer = Cartographer(
        model_name=model_name,
        thinking_level=thinking_level,
        manager=state_manager,
    )

    print(f"Initializing Historian agent ({model_name}, thinking={thinking_level})...", flush=True)
    historian = Historian(
        model_name=model_name,
        thinking_level=thinking_level,
        manager=state_manager,
    )

    # Initial question from Cartographer
    query = cartographer.start_chronicle()

    for turn in range(1, num_turns + 1):
        print(f"\n{'='*35} EPOCH {turn} {'='*35}\n", flush=True)

        print("🧭 CARTOGRAPHER PROMPTS HISTORIAN:", flush=True)
        print(f'"{query}"\n', flush=True)

        print(f"📜 HISTORIAN NARRATES (Epoch {turn}):", flush=True)
        narrative = historian.narrate(query, epoch=turn)
        print(narrative, flush=True)
        print("\n" + "-" * 80 + "\n", flush=True)

        print(f"🗺️ CARTOGRAPHER UPDATES MAP & REGISTRY (Epoch {turn}):", flush=True)
        cartographer_response = cartographer.process_narrative(narrative, epoch=turn)
        print(cartographer_response, flush=True)

        # Verify persistent snapshot on disk
        epoch_file = state_manager.epoch_file_path(turn)
        latest_file = state_manager.latest_file_path
        if epoch_file.exists() and latest_file.exists():
            state = state_manager.load_latest_state() or {}
            loc_count = len(state.get("locations", {}))
            print(f"\n💾 [Persistence Check]:", flush=True)
            print(f"   • Snapshot saved: {epoch_file.name} ({epoch_file.stat().st_size} bytes)", flush=True)
            print(f"   • Latest updated: {latest_file.name} (Epoch {state.get('epoch')}, {loc_count} locations)", flush=True)
        else:
            print(f"\n⚠️ Warning: Expected snapshot files not found for Epoch {turn}.", flush=True)

        # Pass the Cartographer's log and follow-up prompt to the Historian for the next epoch
        if cartographer_response and "?" in cartographer_response:
            query = cartographer_response
        elif cartographer_response:
            query = f"{cartographer_response}\n\nWhat happened next in the chronicle of this land?"
        else:
            query = "What happened next in the chronicle of this land?"

    print("\n" + "=" * 80, flush=True)
    print(" ✅ WORLD BUILDING CHRONICLE SIMULATION COMPLETE", flush=True)
    latest_state = state_manager.load_latest_state()
    if latest_state:
        print(f" Realm: {latest_state.get('realm_name', 'Unknown')}", flush=True)
        print(f" Final Epoch: {latest_state.get('epoch')}", flush=True)
        print(f" Total Locations: {len(latest_state.get('locations', {}))}", flush=True)
        print(f" Canonical Latest File: {state_manager.latest_file_path}", flush=True)
    print("=" * 80, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Cartographer and Historian agent interaction with persistent world state."
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=2,
        help="Number of historical epochs/turns to simulate (default: 2)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.7-flash",
        help="Gemini model to use (default: gemini-3.7-flash)",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        default="HIGH",
        help="Thinking level for Gemini models (default: HIGH)",
    )
    parser.add_argument(
        "--storage-dir",
        type=str,
        default="artifacts/world_state",
        help="Directory to save persistent world snapshots (default: artifacts/world_state)",
    )

    args = parser.parse_args()

    try:
        run_simulation(
            num_turns=args.turns,
            model_name=args.model,
            thinking_level=args.thinking,
            storage_dir=args.storage_dir,
        )
    except Exception as e:
        print(f"\n❌ Error running simulation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
