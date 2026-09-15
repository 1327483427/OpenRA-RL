"""Map and game-mode discovery for the OpenRA AI control platform."""

from __future__ import annotations

import zipfile
import re
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_MODS = ("ra", "cnc", "d2k", "ts")

GAME_MODES = (
    {"id": "skirmish", "name": "Skirmish", "description": "Standard base building and elimination."},
    {"id": "survival", "name": "Survival", "description": "Defend against escalating enemy waves."},
    {"id": "campaign", "name": "Campaign", "description": "Scripted missions with map-specific objectives."},
    {"id": "challenge", "name": "Challenge", "description": "Restricted-unit or objective-based scenarios."},
)


def available_mods(openra_path: str | Path) -> list[str]:
    """Return supported mods that are installed in an OpenRA tree."""
    mods_root = Path(openra_path) / "mods"
    return [mod for mod in SUPPORTED_MODS if (mods_root / mod).is_dir()]


def _map_metadata_from_yaml(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        # OpenRA's MiniYAML files conventionally use tabs for indentation,
        # while standard YAML rejects tabs. Normalizing indentation is safe
        # for the small top-level metadata fields read here.
        data = yaml.safe_load(text.replace("\t", "  ")) or {}
    except yaml.YAMLError:
        # MiniYAML intentionally accepts constructs that strict YAML parsers
        # reject. Fall back to the stable top-level fields used by the UI.
        def top_level(name: str) -> str:
            match = re.search(rf"^{re.escape(name)}:\s*(.*?)\s*$", text, re.MULTILINE)
            return match.group(1).strip("\"'") if match else ""

        players_match = re.search(r"^Players:\s*$([\s\S]*?)(?=^[A-Za-z][^\n]*:\s*$)", text, re.MULTILINE)
        player_names = []
        if players_match:
            player_names = re.findall(r"^[ \t]+PlayerReference@([^:\n]+):", players_match.group(1), re.MULTILINE)
        player_count = sum(1 for name in player_names if name.lower() not in {"neutral", "creeps"})
        categories = [item.strip() for item in top_level("Categories").split(",") if item.strip()]
        return {
            "title": top_level("Title"),
            "author": top_level("Author"),
            "categories": categories,
            "players": player_count,
            "bounds": top_level("Bounds"),
        }

    players = data.get("Players")
    player_count = 0
    if isinstance(players, dict):
        player_count = sum(
            1 for name in players if str(name).lower() not in {"playerreference@neutral", "playerreference@creeps"}
        )

    categories = data.get("Categories", [])
    if isinstance(categories, str):
        categories = [item.strip() for item in categories.split(",") if item.strip()]

    bounds = data.get("Bounds")
    return {
        "title": data.get("Title") or data.get("MapTitle") or "",
        "author": data.get("Author") or "",
        "categories": categories if isinstance(categories, list) else [],
        "players": player_count,
        "bounds": bounds or "",
    }


def _read_packaged_map_metadata(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            return _map_metadata_from_yaml(archive.read("map.yaml"))
    except (OSError, KeyError, zipfile.BadZipFile):
        return {}


def discover_maps(
    openra_path: str | Path,
    mod: str = "ra",
    include_campaigns: bool = False,
) -> list[dict[str, Any]]:
    """Discover packaged skirmish maps and optionally unpacked campaign maps."""
    if mod not in SUPPORTED_MODS:
        raise ValueError(f"Unsupported mod: {mod}")

    maps_root = Path(openra_path) / "mods" / mod / "maps"
    if not maps_root.is_dir():
        return []

    maps: list[dict[str, Any]] = []
    for path in sorted(maps_root.glob("*.oramap"), key=lambda item: item.name.lower()):
        metadata = _read_packaged_map_metadata(path)
        maps.append({
            "map_name": path.name,
            "title": metadata.get("title") or path.stem.replace("-", " ").title(),
            "author": metadata.get("author", ""),
            "categories": metadata.get("categories", []),
            "players": metadata.get("players", 0),
            "bounds": metadata.get("bounds", ""),
            "kind": "skirmish",
            "mod": mod,
        })

    if include_campaigns:
        for path in sorted(maps_root.glob("*/map.yaml"), key=lambda item: item.parent.name.lower()):
            metadata = _map_metadata_from_yaml(path.read_bytes())
            maps.append({
                "map_name": path.parent.name,
                "title": metadata.get("title") or path.parent.name.replace("-", " ").title(),
                "author": metadata.get("author", ""),
                "categories": metadata.get("categories", []),
                "players": metadata.get("players", 0),
                "bounds": metadata.get("bounds", ""),
                "kind": "campaign",
                "mod": mod,
            })

    return maps
