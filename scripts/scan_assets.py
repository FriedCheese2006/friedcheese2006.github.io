"""
Sync game assets from a UE4 export directory into the web app's public folder.

Usage:
    python3 scripts/scan_assets.py /path/to/Ue4Export

It performs these operations:
    1. Copies the six source JSON data files from the export directory.
  2. Walks D_Itemable.json to find every item icon that should exist.
  3. Copies new/updated icons from the UE4 export into public/icarus-game/ItemIcons/.
  4. Removes (orphaned) icons that are no longer referenced or no longer present
     in the UE4 export directory.
    5. Generates the normalized crafting catalog consumed by the frontend.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

try:
    from scripts.icarus_catalog import build_catalog, diagnostic_counts, load_table
except ModuleNotFoundError:
    from icarus_catalog import build_catalog, diagnostic_counts, load_table

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ITEM_ICONS_UE4_SUBPATH = Path("Icarus", "Content", "Assets", "2DArt", "UI", "Items", "Item_Icons")
PUBLIC_FILE_MODE = 0o600

SOURCE_DATA_FILES: dict[str, str] = {
    "D_Itemable.json": "Traits/D_Itemable.json",
    "D_ItemsStatic.json": "Items/D_ItemsStatic.json",
    "D_ItemTemplate.json": "Items/D_ItemTemplate.json",
    "D_ProcessorRecipes.json": "Crafting/D_ProcessorRecipes.json",
    "D_ExtractorRecipes.json": "Crafting/D_ExtractorRecipes.json",
    "D_RecipeSets.json": "Crafting/D_RecipeSets.json",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ParsedAsset:
    categories: list[str]
    name: str
    ext: str
    has_duplicated_name: bool
    web_loc_exist: bool
    ua_asset_name: str
    ua_asset_path: Path
    ua_asset_path_exist: bool
    full_path_name: Path
    path_web_relative: Optional[str] = None
    in_itemable_files: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def walk(start_dir: Path) -> Iterator[Path]:
    """Recursively yield every *file* under start_dir."""
    for entry in sorted(start_dir.iterdir()):
        if entry.is_dir():
            yield from walk(entry)
        elif entry.is_file():
            yield entry


def parse_asset(
    full_path: Path,
    ue4_export_dir: Path,
    web_loc_exist: bool,
) -> ParsedAsset:
    """Extract metadata about an asset file path."""
    parts = full_path.parts
    try:
        icons_idx = parts.index("ItemIcons")
    except ValueError:
        raise ValueError(f"'ItemIcons' not found in path: {full_path}")

    relative_parts = list(parts[icons_idx + 1 :])
    categories = relative_parts[:-1]

    stem = full_path.stem
    stem_parts = stem.split(".")
    has_duplicated_name = len(stem_parts) == 2 and stem_parts[0] == stem_parts[1]

    ua_asset_name = full_path.name
    ua_asset_path = ue4_export_dir / ITEM_ICONS_UE4_SUBPATH / Path(*categories, ua_asset_name) if categories else ue4_export_dir / ITEM_ICONS_UE4_SUBPATH / ua_asset_name

    return ParsedAsset(
        categories=categories,
        name=full_path.stem,
        ext=full_path.suffix,
        has_duplicated_name=has_duplicated_name,
        web_loc_exist=web_loc_exist,
        ua_asset_name=ua_asset_name,
        ua_asset_path=ua_asset_path,
        ua_asset_path_exist=ua_asset_path.exists(),
        full_path_name=full_path,
    )


def _make_relative(icon_str: str, anchor: str) -> Optional[str]:
    """
    Strip everything up to and including *anchor* from a path string.
    Also strips the .png extension and the UE4 object-reference suffix
    (e.g. 'Name.Name' → 'Name').
    """
    parts = icon_str.replace("\\", "/").split("/")
    try:
        idx = parts.index(anchor)
    except ValueError:
        return None
    relative = "/".join(parts[idx + 1 :])

    # Strip .png
    if relative.endswith(".png"):
        relative = relative[: -len(".png")]

    # Strip UE4 object-reference suffix (AssetName.ObjectName → AssetName)
    dot_idx = relative.rfind(".")
    if dot_idx >= 0:
        relative = relative[:dot_idx]

    return relative or None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def parse_assets_from_data_file(
    base_web_loc: Path,
    ue4_export_dir: Path,
    itemables: dict,
) -> Iterator[ParsedAsset]:
    """Yield a ParsedAsset for every icon referenced in D_Itemable.json."""
    base_icons = base_web_loc / "ItemIcons"

    for row in itemables.get("Rows", []):
        icon: Optional[str] = row.get("Icon")
        if not icon:
            continue

        parts = icon.replace("\\", "/").split("/")
        try:
            icons_idx = parts.index("Item_Icons")
        except ValueError:
            continue

        relative_parts = parts[icons_idx + 1 :]

        # Strip UE4 object-reference suffix from the last component
        last = relative_parts[-1]
        dot_idx = last.rfind(".")
        if dot_idx >= 0:
            relative_parts[-1] = last[:dot_idx]

        web_path = base_icons.joinpath(*relative_parts).with_suffix(".png")
        yield parse_asset(web_path, ue4_export_dir, web_path.exists())


def find_orphaned_assets(
    base_web_loc: Path,
    ue4_export_dir: Path,
    itemables: dict,
) -> Iterator[tuple[ParsedAsset, None]]:
    """Yield assets in ItemIcons/ that are no longer in the data file or UE4 export."""
    base_icons = base_web_loc / "ItemIcons"

    referenced = {
        _make_relative(row["Icon"], "Item_Icons")
        for row in itemables.get("Rows", [])
        if row.get("Icon")
    }
    referenced.discard(None)

    for file_path in walk(base_icons):
        asset = parse_asset(file_path, ue4_export_dir, file_path.exists())
        path_web_relative = _make_relative(str(file_path), "ItemIcons")
        asset.path_web_relative = path_web_relative
        asset.in_itemable_files = path_web_relative in referenced

        if not asset.ua_asset_path_exist or not asset.in_itemable_files:
            yield asset, None


def copy_file(src: Path, dst: Path, existed: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    copy_public_file(src, dst)
    verb = "replaced" if existed else "created"
    print(f"{src} => {dst} {verb} successfully.")


def copy_public_file(src: Path, dst: Path) -> None:
    shutil.copy2(src, dst)
    os.chmod(dst, PUBLIC_FILE_MODE)


def update_source_data_files(web_public_data: Path, ue4_export_dir: Path) -> None:
    failures: list[str] = []
    for dest_name, src_rel in SOURCE_DATA_FILES.items():
        src = ue4_export_dir / src_rel
        dst = web_public_data / dest_name
        try:
            copy_public_file(src, dst)
            print(f"{src} => {dst} copied successfully.")
        except OSError as exc:
            failures.append(f"{src}: {exc}")
            print(f"ERROR: {src} => {dst} failed to copy: {exc}", file=sys.stderr)
    if failures:
        raise RuntimeError("Unable to update all source data files:\n" + "\n".join(failures))


def generate_crafting_catalog(base_web_loc: Path) -> None:
    data_dir = base_web_loc / "Data"
    overrides_path = Path(__file__).with_name("icarus_catalog_overrides.json")
    overrides = load_table(overrides_path, required=False)
    catalog = build_catalog(data_dir, base_web_loc / "ItemIcons", overrides)
    output_path = data_dir / "D_CraftingCatalog.json"
    output_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {output_path}")
    print("Catalog diagnostics:", json.dumps(diagnostic_counts(catalog), sort_keys=True))


def update_game_assets(base_web_loc: Path, ue4_export_dir: Path) -> None:
    itemable_path = base_web_loc / "Data" / "D_Itemable.json"
    with open(itemable_path, encoding="utf-8") as fh:
        itemables = json.load(fh)

    missing: list[ParsedAsset] = []

    for asset in parse_assets_from_data_file(base_web_loc, ue4_export_dir, itemables):
        if not asset.ua_asset_path_exist:
            missing.append(asset)
            continue
        try:
            copy_file(asset.ua_asset_path, asset.full_path_name, asset.web_loc_exist)
        except OSError as exc:
            print(
                f"ERROR: {asset.ua_asset_path} => {asset.full_path_name} failed: {exc}",
                file=sys.stderr,
            )

    if missing:
        print("Cannot find these assets in the extracted assets directory:")
        for a in missing:
            print(" ", json.dumps({"name": a.ua_asset_name, "path": str(a.ua_asset_path)}))

    orphan_header_printed = False
    for asset, _ in find_orphaned_assets(base_web_loc, ue4_export_dir, itemables):
        if not orphan_header_printed:
            print(
                "Orphaned Assets\n"
                "****** These are assets in the web ItemIcons folder that either do not\n"
                "       exist in the extracted assets folder, or are not referenced in\n"
                "       D_Itemable.json."
            )
            orphan_header_printed = True
        print(" ", asset.name)
        asset.full_path_name.unlink(missing_ok=True)

    generate_crafting_catalog(base_web_loc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    base_web_loc = Path("public") / "icarus-game"
    if not base_web_loc.exists():
        print("ERROR: Unable to find public/icarus-game", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        prog = sys.argv[0]
        print(f"USAGE: python3 {prog} Ue4ExportDir", file=sys.stderr)
        sys.exit(1)

    ue4_export_dir = Path(sys.argv[1]).resolve()
    if not ue4_export_dir.exists():
        print(f"ERROR: Export directory not found: {ue4_export_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Export dir: {ue4_export_dir}")

    print("Updating web app game data …")
    update_source_data_files(base_web_loc / "Data", ue4_export_dir)

    print("Updating web game assets …")
    update_game_assets(base_web_loc, ue4_export_dir)


if __name__ == "__main__":
    main()
