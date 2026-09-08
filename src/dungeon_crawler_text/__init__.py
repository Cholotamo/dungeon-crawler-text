"""dungeon_crawler_text package."""

from typing import TYPE_CHECKING, Any

from dungeon_crawler_text.historian import (
    Historian,
    HistorianEpochResult,
    WorldStateSnapshot,
    resolve_epoch_paths,
)
from dungeon_crawler_text.loremaster import (
    DEFAULT_PRIMORDIAL_QUERY,
    Loremaster,
)
from dungeon_crawler_text.world_state import format_world_for_llm

if TYPE_CHECKING:
    from dungeon_crawler_text.architect import (
        DEFAULT_INPUT_PROSE_PATH,
        DEFAULT_OUTPUT_MAP_PATH,
        Architect,
    )
    from dungeon_crawler_text.viewer import (
        build_viewer_html,
        generate_html_viewer,
        open_viewer,
        serve_viewer,
    )


def __getattr__(name: str) -> Any:
    if name in ("Architect", "DEFAULT_INPUT_PROSE_PATH", "DEFAULT_OUTPUT_MAP_PATH"):
        from dungeon_crawler_text import architect

        return getattr(architect, name)
    if name in ("build_viewer_html", "generate_html_viewer", "open_viewer", "serve_viewer"):
        from dungeon_crawler_text import viewer

        return getattr(viewer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Architect",
    "DEFAULT_INPUT_PROSE_PATH",
    "DEFAULT_OUTPUT_MAP_PATH",
    "Historian",
    "HistorianEpochResult",
    "Loremaster",
    "DEFAULT_PRIMORDIAL_QUERY",
    "WorldStateSnapshot",
    "build_viewer_html",
    "format_world_for_llm",
    "generate_html_viewer",
    "open_viewer",
    "resolve_epoch_paths",
    "serve_viewer",
]
