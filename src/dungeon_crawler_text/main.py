"""Main entry point for running the Historian narrative world-building generation."""

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dungeon_crawler_text.historian import (
    Historian,
    extract_chronology,
    extract_historian_prose,
)


def run_historian_simulation(
    num_epochs: int = 2,
    model_name: str = "gemini-3.7-flash",
    thinking_level: str = "HIGH",
    initial_query: str = (
        "Describe the primordial geography of a temperate fantasy realm: "
        "its natural boundaries, coastlines, mountain ridges, and waterways."
    ),
    epoch_query: str = "What happened next in the chronicle of this land?",
    output_dir: Path | None = None,
) -> None:
    """Runs a multi-epoch narrative generation using the Historian agent."""
    load_dotenv()

    print("=" * 80, flush=True)
    print(" HISTORIAN WORLD-BUILDER: PROSE CHRONICLE GENERATION", flush=True)
    print("=" * 80, flush=True)

    print(
        f"\nInitializing Historian agent ({model_name}, thinking={thinking_level}, memory=True)...",
        flush=True,
    )
    historian = Historian(model_name=model_name, thinking_level=thinking_level)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, num_epochs + 1):
        print(f"\n{'='*35} EPOCH {epoch} {'='*35}\n", flush=True)

        if epoch == 1:
            print("QUERY TO HISTORIAN (PRIMORDIAL FOUNDATIONS):", flush=True)
            print(f'"{initial_query}"\n', flush=True)
            raw_narrative = historian.generate_primordial_world(initial_query)
        else:
            print(f"QUERY TO HISTORIAN (EPOCH {epoch}):", flush=True)
            print(f'"{epoch_query}"\n', flush=True)
            raw_narrative = historian.chronicle_epoch(epoch=epoch, query=epoch_query)

        chrono = extract_chronology(raw_narrative, epoch=epoch)
        prose = extract_historian_prose(raw_narrative)

        print(f"--- CANONICAL CHRONOLOGY (EPOCH {epoch}) ---", flush=True)
        print(f"Reckoning:     {chrono.get('reckoning', 'Unspecified')}", flush=True)
        print(f"Elapsed Time:  {chrono.get('years_passed', 'Unspecified')}\n", flush=True)

        print("--- HISTORIAN PROSE ---", flush=True)
        print(prose, flush=True)
        print("\n" + "-" * 80, flush=True)

        if output_dir:
            file_path = output_dir / f"chronicle_epoch_{epoch}.md"
            content = (
                f"# Epoch {epoch}: {chrono.get('reckoning', 'Chronicle')}\n\n"
                f"**Years Passed:** {chrono.get('years_passed', 'Unspecified')}\n\n"
                f"## Narrative\n\n{prose}\n"
            )
            file_path.write_text(content, encoding="utf-8")
            print(f"Epoch chronicle saved to: {file_path}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(" TOKEN USAGE SUMMARY", flush=True)
    print("=" * 80, flush=True)
    usage = historian.token_usage
    print(f"Prompt Tokens:     {usage['prompt_tokens']:,}", flush=True)
    print(f"Candidate Tokens:  {usage['candidates_tokens']:,}", flush=True)
    if usage.get("thoughts_tokens"):
        print(f"Thoughts Tokens:   {usage['thoughts_tokens']:,}", flush=True)
    print(f"Total Tokens:      {usage['total_tokens']:,}", flush=True)
    print("=" * 80, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Historian world-building prose generation."
    )
    parser.add_argument(
        "--epochs",
        "--turns",
        dest="epochs",
        type=int,
        default=2,
        help="Number of historical epochs to chronicle (default: 2)",
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
        "--output-dir",
        type=str,
        default=None,
        help="Optional directory to save epoch chronicle Markdown files",
    )

    args = parser.parse_args()

    try:
        run_historian_simulation(
            num_epochs=args.epochs,
            model_name=args.model,
            thinking_level=args.thinking,
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
    except Exception as e:
        print(f"\n[ERROR] Simulation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
