"""Main entry point for generating the primordial fantasy realm description."""

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dungeon_crawler_text.worldbuilder import DEFAULT_PRIMORDIAL_QUERY, WorldBuilder


def generate_primordial_landscape(
    model_name: str = "gemini-3.6-flash",
    thinking_level: str = "MEDIUM",
    query: str = DEFAULT_PRIMORDIAL_QUERY,
    output_path: Path | None = None,
) -> str:
    """Generates a primordial world description using the WorldBuilder agent."""
    load_dotenv()

    print("=" * 80, flush=True)
    print(" WORLDBUILDER: PRIMORDIAL LANDSCAPE", flush=True)
    print("=" * 80, flush=True)

    print(
        f"\nInitializing WorldBuilder agent ({model_name}, thinking={thinking_level})...",
        flush=True,
    )
    worldbuilder = WorldBuilder(model_name=model_name, thinking_level=thinking_level)

    print("\nQUERY TO WORLDBUILDER:", flush=True)
    print(f'"{query}"\n', flush=True)

    narrative = worldbuilder.generate_primordial_world(query=query)

    print("--- PRIMORDIAL LANDSCAPE NARRATIVE ---", flush=True)
    print(narrative, flush=True)
    print("\n" + "-" * 80, flush=True)

    if output_path:
        if output_path.is_dir() or output_path.suffix == "":
            output_path.mkdir(parents=True, exist_ok=True)
            target_file = output_path / "primordial_landscape.md"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            target_file = output_path

        content = (
            "# Primordial Landscape\n\n"
            f"**Query:** {query}\n\n"
            f"## Narrative\n\n{narrative}\n"
        )
        target_file.write_text(content, encoding="utf-8")
        print(f"Primordial landscape saved to: {target_file}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(" TOKEN USAGE SUMMARY", flush=True)
    print("=" * 80, flush=True)
    usage = worldbuilder.token_usage
    print(f"Prompt Tokens:     {usage['prompt_tokens']:,}", flush=True)
    print(f"Candidate Tokens:  {usage['candidates_tokens']:,}", flush=True)
    if usage.get("thoughts_tokens"):
        print(f"Thoughts Tokens:   {usage['thoughts_tokens']:,}", flush=True)
    print(f"Total Tokens:      {usage['total_tokens']:,}", flush=True)
    print("=" * 80, flush=True)

    return narrative


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a primordial fantasy realm description using the WorldBuilder agent."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.6-flash",
        help="Gemini model to use (default: gemini-3.6-flash)",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        default="MEDIUM",
        help="Thinking level for Gemini models (default: MEDIUM)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=DEFAULT_PRIMORDIAL_QUERY,
        help="Custom prompt query to ask the WorldBuilder",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Optional file path or directory to save the output Markdown file",
    )

    args = parser.parse_args()

    try:
        generate_primordial_landscape(
            model_name=args.model,
            thinking_level=args.thinking,
            query=args.query,
            output_path=Path(args.output) if args.output else None,
        )
    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
