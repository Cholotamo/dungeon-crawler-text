"""dungeon_crawler_text package."""

from typing import TYPE_CHECKING, Any

from dungeon_crawler_text.historian import (
    DEFAULT_EPOCH_1_QUERY,
    DEFAULT_SUBSEQUENT_EPOCH_QUERY,
    Historian,
    HistorianEpochResult,
    ToolRejectionError,
    WorldStateSnapshot,
    calculate_cost,
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
    from dungeon_crawler_text.dossier import (
        harvest_all_dossiers,
        harvest_landmark_keyframes,
    )
    from dungeon_crawler_text.viewer import (
        build_viewer_html,
        generate_html_viewer,
        open_viewer,
        serve_viewer,
    )
    from dungeon_crawler_text.subarchitect import (
        Subarchitect,
        format_localemap_for_llm,
        validate_localemap,
    )


def __getattr__(name: str) -> Any:
    if name in ("Architect", "DEFAULT_INPUT_PROSE_PATH", "DEFAULT_OUTPUT_MAP_PATH"):
        from dungeon_crawler_text import architect

        return getattr(architect, name)
    if name in ("harvest_all_dossiers", "harvest_landmark_keyframes"):
        from dungeon_crawler_text import dossier

        return getattr(dossier, name)
    if name in ("generate_locale_seed", "generate_all_locale_seeds"):
        from dungeon_crawler_text import seed

        return getattr(seed, name)
    if name in ("build_viewer_html", "generate_html_viewer", "open_viewer", "serve_viewer"):
        from dungeon_crawler_text import viewer

        return getattr(viewer, name)
    if name in ("Subarchitect", "SubArchitect", "validate_localemap", "format_localemap_for_llm"):
        from dungeon_crawler_text import subarchitect

        return getattr(subarchitect, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Architect",
    "DEFAULT_INPUT_PROSE_PATH",
    "DEFAULT_OUTPUT_MAP_PATH",
    "DEFAULT_PRIMORDIAL_QUERY",
    "DEFAULT_EPOCH_1_QUERY",
    "DEFAULT_SUBSEQUENT_EPOCH_QUERY",
    "Historian",
    "HistorianEpochResult",
    "Loremaster",
    "SubArchitect",
    "Subarchitect",
    "ToolRejectionError",
    "WorldStateSnapshot",
    "build_viewer_html",
    "calculate_cost",
    "format_localemap_for_llm",
    "format_world_for_llm",
    "generate_all_locale_seeds",
    "generate_html_viewer",
    "generate_locale_seed",
    "harvest_all_dossiers",
    "harvest_landmark_keyframes",
    "open_viewer",
    "resolve_epoch_paths",
    "serve_viewer",
    "validate_localemap",
]
