#!/usr/bin/env python3
"""
build_viewer.py - Build the retro CLI terminal map viewer.

Reads all worldmap*.json and locale data from artifacts/ and produces
a self-contained viewer.html with all data embedded.

Usage:
    python build_viewer.py
"""

import json
from pathlib import Path

ARTIFACTS = Path(__file__).parent / "artifacts"
TEMPLATE_FILE = Path(__file__).parent / "viewer_template.html"
OUTPUT = Path(__file__).parent / "viewer.html"


def load_epochs():
    """Load all worldmap epoch JSON files into an epoch-keyed dict."""
    epochs = {}

    # Primordial era (epoch 0)
    wm = ARTIFACTS / "worldmap.json"
    if wm.exists():
        data = json.loads(wm.read_text(encoding="utf-8"))
        epochs[0] = data

    # Numbered epochs
    for p in sorted(ARTIFACTS.glob("worldmap_epoch_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        epoch = data.get("epoch", 0)
        epochs[epoch] = data

    return epochs


def load_locales():
    """Load all locale keyframe and dossier data."""
    locales = {}
    locales_dir = ARTIFACTS / "locales"
    if not locales_dir.is_dir():
        return locales

    for d in sorted(locales_dir.iterdir()):
        if not d.is_dir():
            continue

        feature_id = d.name
        entry = {"keyframes": {}, "dossier": None}

        # Dossier
        dossier = d / "dossier.json"
        if dossier.exists():
            entry["dossier"] = json.loads(dossier.read_text(encoding="utf-8"))

        # Keyframes (keyed by epoch number)
        for kf in sorted(d.glob("localemap_keyframe_*.json")):
            data = json.loads(kf.read_text(encoding="utf-8"))
            ep = data.get("epoch", 0)
            entry["keyframes"][ep] = data

        if entry["keyframes"]:
            locales[feature_id] = entry

    return locales


def main():
    print("Loading epoch data...")
    epochs = load_epochs()

    print("Loading locale data...")
    locales = load_locales()

    print("Reading template...")
    template = TEMPLATE_FILE.read_text(encoding="utf-8")

    # Serialize data with compact JSON
    epochs_json = json.dumps(epochs, separators=(",", ":"))
    locales_json = json.dumps(locales, separators=(",", ":"))

    # Prevent </script> in data strings from breaking the HTML
    epochs_json = epochs_json.replace("</", "<\\/")
    locales_json = locales_json.replace("</", "<\\/")

    # Inject data into template
    html = template.replace('"%%EPOCHS%%"', epochs_json)
    html = html.replace('"%%LOCALES%%"', locales_json)

    # Write output files
    OUTPUT.write_text(html, encoding="utf-8")
    artifacts_out = ARTIFACTS / "viewer.html"
    artifacts_out.write_text(html, encoding="utf-8")

    print(f"\nBuilt: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"Built: {artifacts_out} ({artifacts_out.stat().st_size:,} bytes)")
    ne = len(epochs)
    nl = len(locales)
    nk = sum(len(loc["keyframes"]) for loc in locales.values())
    print(f"  {ne} epochs, {nl} locales ({nk} total keyframes)")


if __name__ == "__main__":
    main()
