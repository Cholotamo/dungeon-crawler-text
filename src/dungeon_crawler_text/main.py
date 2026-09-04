"""Main entry point for running the Cartographer & Historian world-building simulation."""

import argparse
import copy
from pathlib import Path
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dungeon_crawler_text.cartographer import Cartographer
from dungeon_crawler_text.historian import Historian
from dungeon_crawler_text.world_state import (
    format_snapshot_injection,
    render_composite_map,
    save_snapshot_file,
)


def run_simulation(
    num_turns: int = 3,
    model_name: str = "gemini-3.7-flash",
    thinking_level: str = "HIGH",
    artifacts_dir: Path = Path("artifacts"),
) -> None:
    """Initializes Cartographer and Historian agents and runs their multi-turn collaboration.

    Follows the optimized process:
    - Historian maintains chat memory across epochs.
    - Cartographer:
        * Turn 1: Generates primordial canvas via procedural code execution.
        * Turn 2+: Evolves world state statelessly via fine-grained mutation tools (AFC).
    - Snapshots are versioned and managed per epoch by the Python runner.
    - Composite maps are rendered from snapshots and displayed with stacked coordinates.
    """
    load_dotenv()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80, flush=True)
    print(" WORLD BUILDER SIMULATION: CARTOGRAPHER & HISTORIAN", flush=True)
    print("=" * 80, flush=True)

    print(
        f"\nInitializing Cartographer agent ({model_name}, thinking={thinking_level}, stateless=True)...",
        flush=True,
    )
    cartographer = Cartographer(model_name=model_name, thinking_level=thinking_level)

    print(
        f"Initializing Historian agent ({model_name}, thinking={thinking_level}, memory=True)...",
        flush=True,
    )
    historian = Historian(model_name=model_name, thinking_level=thinking_level)

    current_state: dict = {}
    last_log: str = ""
    query = cartographer.start_chronicle()

    for turn in range(1, num_turns + 1):
        print(f"\n{'='*35} TURN {turn} (EPOCH {turn}) {'='*35}\n", flush=True)

        if turn == 1:
            print("CARTOGRAPHER PROMPTS HISTORIAN (PRIMORDIAL CREATION):", flush=True)
            print(f'"{query}"\n', flush=True)

            print("HISTORIAN NARRATES PRIMORDIAL LAND:", flush=True)
            narrative = historian.generate_primordial_world(query)
            print(narrative, flush=True)
            print("\n" + "-" * 80 + "\n", flush=True)

            print("CARTOGRAPHER GENERATES BASELINE MAP VIA CODE EXECUTION...", flush=True)
            snapshot, log, _ = cartographer.generate_primordial_map(narrative)
            last_log = log
        else:
            print("HISTORIAN INSPECTS DUAL-GRID WORLD STATE & NARRATES...", flush=True)
            snapshot_injection = format_snapshot_injection(current_state)
            narrative = historian.chronicle_epoch(
                snapshot_injection=snapshot_injection,
                cartographer_log=last_log,
                epoch=turn,
                query=query,
            )
            print(narrative, flush=True)
            print("\n" + "-" * 80 + "\n", flush=True)

            # Python runner handles snapshot management:
            # Clone previous epoch state and create new snapshot file
            current_state = copy.deepcopy(current_state)
            current_state["epoch"] = turn
            epoch_snapshot_path = save_snapshot_file(current_state, artifacts_dir, epoch=turn)
            print(f"Initialized Epoch {turn} snapshot: {epoch_snapshot_path.name}", flush=True)

            print("CARTOGRAPHER EVOLVES WORLD MAP VIA MUTATION TOOLS...", flush=True)
            snapshot, log, _ = cartographer.evolve_map(
                historian_narrative=narrative,
                previous_state=current_state,
                epoch=turn,
                snapshot_path=epoch_snapshot_path,
            )
            last_log = log

        if snapshot:
            current_state = snapshot
            current_state["epoch"] = turn
            saved_path = save_snapshot_file(current_state, artifacts_dir, epoch=turn)
            print(f"World state snapshot saved to: {saved_path}", flush=True)

            print("\nRENDERED ASCII COMPOSITE MAP (EPOCH {0}):".format(turn), flush=True)
            rendered_map = render_composite_map(current_state)
            print(rendered_map, flush=True)
        else:
            print(
                "\n[WARNING] Could not parse structured world state snapshot from Cartographer output.",
                flush=True,
            )

        if last_log:
            print(f"\nCARTOGRAPHIC LOG (EPOCH {turn}):", flush=True)
            print(last_log, flush=True)

        query = "What happened next in the chronicle of this land?"

    print("\n" + "=" * 80, flush=True)
    print(" SIMULATION TOKEN USAGE SUMMARY", flush=True)
    print("=" * 80, flush=True)

    h_usage = historian.token_usage
    c_usage = cartographer.token_usage
    tot_prompt = h_usage["prompt_tokens"] + c_usage["prompt_tokens"]
    tot_candidates = h_usage["candidates_tokens"] + c_usage["candidates_tokens"]
    tot_thoughts = h_usage["thoughts_tokens"] + c_usage["thoughts_tokens"]
    grand_total = h_usage["total_tokens"] + c_usage["total_tokens"]

    print("Historian Agent:", flush=True)
    print(f"   - Prompt Tokens:     {h_usage['prompt_tokens']:,}", flush=True)
    print(f"   - Completion Tokens: {h_usage['candidates_tokens']:,}", flush=True)
    if h_usage['thoughts_tokens']:
        print(f"   - Thoughts Tokens:   {h_usage['thoughts_tokens']:,}", flush=True)
    print(f"   - Total Tokens:      {h_usage['total_tokens']:,}\n", flush=True)

    print("Cartographer Agent (Stateless):", flush=True)
    print(f"   - Prompt Tokens:     {c_usage['prompt_tokens']:,}", flush=True)
    print(f"   - Completion Tokens: {c_usage['candidates_tokens']:,}", flush=True)
    if c_usage['thoughts_tokens']:
        print(f"   - Thoughts Tokens:   {c_usage['thoughts_tokens']:,}", flush=True)
    print(f"   - Total Tokens:      {c_usage['total_tokens']:,}\n", flush=True)

    print(f"Grand Total Usage across {num_turns} Epochs:", flush=True)
    print(f"   - Prompt Tokens:     {tot_prompt:,}", flush=True)
    print(f"   - Completion Tokens: {tot_candidates:,}", flush=True)
    if tot_thoughts:
        print(f"   - Thoughts Tokens:   {tot_thoughts:,}", flush=True)
    print(f"   - Combined Total:    {grand_total:,}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(" WORLD BUILDING CHRONICLE SIMULATION COMPLETE", flush=True)
    print(f"Snapshots saved to: {artifacts_dir.resolve()}", flush=True)
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
        "--artifacts",
        type=str,
        default="artifacts",
        help="Directory to save snapshot artifacts (default: artifacts)",
    )

    args = parser.parse_args()

    try:
        run_simulation(
            num_turns=args.turns,
            model_name=args.model,
            thinking_level=args.thinking,
            artifacts_dir=Path(args.artifacts),
        )
    except Exception as e:
        print(f"\n[ERROR] Error running simulation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
