from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
FALLBACK_IMAGE_PATH = "/icarus-game/Images/question-mark.png"
ITEM_ICON_PREFIX = "/Game/Assets/2DArt/UI/Items/Item_Icons/"
FOOD_TAG_PREFIX = "Item.Consumable.Food"
FOOD_TAGS = {"FieldGuide.Food", "Item.Resource.Spoilable"}
RECIPE_TABLES = (
    ("processor", "D_ProcessorRecipes.json"),
    ("extractor", "D_ExtractorRecipes.json"),
)


def load_table(path: Path, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {"Rows": []}
    with path.open(encoding="utf-8") as file_handle:
        return json.load(file_handle)


def clean_display_text(value: str | None) -> str | None:
    if not value or value == "None":
        return None
    match = re.match(r'^NSLOCTEXT\(".*?",\s*".*?",\s*"(.*)"\)$', value)
    return (match.group(1) if match else value).replace("\\'", "'")


def normalize_item_icon_path(value: str | None) -> str | None:
    if not value or value == "None" or not value.startswith(ITEM_ICON_PREFIX):
        return None
    relative_path = value.removeprefix(ITEM_ICON_PREFIX).replace("\\", "/")
    asset_path, separator, object_name = relative_path.rpartition(".")
    if separator and object_name == Path(asset_path).name:
        relative_path = asset_path
    return f"/icarus-game/ItemIcons/{relative_path}.png"


def row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["Name"]: row for row in rows if row.get("Name")}


def casefold_map(values: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        result.setdefault(value.casefold(), value)
    return result


def has_gameplay_tag_prefix(row: dict[str, Any], prefix: str) -> bool:
    return any(
        tag.get("TagName", "").startswith(prefix)
        for tag_group in ("Manual_Tags", "Generated_Tags")
        for tag in row.get(tag_group, {}).get("GameplayTags", [])
    )


def has_gameplay_tag(row: dict[str, Any], expected: str) -> bool:
    return any(
        tag.get("TagName") == expected
        for tag_group in ("Manual_Tags", "Generated_Tags")
        for tag in row.get(tag_group, {}).get("GameplayTags", [])
    )


def is_food_item(row: dict[str, Any]) -> bool:
    return has_gameplay_tag_prefix(row, FOOD_TAG_PREFIX) or any(has_gameplay_tag(row, tag) for tag in FOOD_TAGS)


class ItemResolver:
    def __init__(
        self,
        template_rows: list[dict[str, Any]],
        static_rows: list[dict[str, Any]],
        itemable_rows: list[dict[str, Any]],
        icons_dir: Path,
        overrides: dict[str, Any],
    ) -> None:
        self.templates = row_map(template_rows)
        self.statics = row_map(static_rows)
        self.itemables = row_map(itemable_rows)
        self.templates_casefold = casefold_map(self.templates)
        self.statics_casefold = casefold_map(self.statics)
        self.itemables_casefold = casefold_map(self.itemables)
        self.icons_dir = icons_dir
        self.overrides = overrides
        self.items: dict[str, dict[str, Any]] = {}
        self.aliases: dict[str, str] = {}
        self.diagnostics: dict[str, list[Any]] = {
            "aliasCollisions": [],
            "missingIconFiles": [],
            "missingItemableRows": [],
            "placeholderItems": [],
        }
        self._build_static_items()

    def resolve_resource(self, raw_id: str | None) -> tuple[str | None, float, str | None]:
        if not raw_id or raw_id == "None":
            return None, 1, None
        resource = self.overrides.get("resourceTypes", {}).get(raw_id, {})
        if raw_id not in self.items:
            image_path = resource.get("imagePath") or FALLBACK_IMAGE_PATH
            self.items[raw_id] = {
                "id": raw_id,
                "label": resource.get("label") or raw_id.replace("_", " "),
                "imagePath": image_path,
                "itemableId": None,
                "templateIds": [],
                "isPlaceholder": False,
                "isResource": True,
                "isFood": resource.get("isFood", False),
                "quantityUnit": resource.get("quantityUnit") or "L",
            }
            self._register_alias(raw_id, raw_id)
            if image_path.startswith("/icarus-game/ItemIcons/"):
                disk_path = self.icons_dir / image_path.removeprefix("/icarus-game/ItemIcons/")
                if not disk_path.exists():
                    self.diagnostics["missingIconFiles"].append({"itemId": raw_id, "imagePath": image_path})
        return raw_id, resource.get("unitsPerQuantity", 1000), self.items[raw_id]["quantityUnit"]

    def _register_alias(self, alias: str | None, item_id: str) -> None:
        if not alias:
            return
        existing = self.aliases.get(alias)
        if existing and existing != item_id:
            self.diagnostics["aliasCollisions"].append({"alias": alias, "itemIds": sorted([existing, item_id])})
            return
        self.aliases[alias] = item_id

    def _build_static_items(self) -> None:
        templates_by_static: dict[str, list[str]] = defaultdict(list)
        for template_id, template in self.templates.items():
            static_id = self._find_static_id(template.get("ItemStaticData", {}).get("RowName"))
            if static_id:
                templates_by_static[static_id].append(template_id)

        for item_id, static_row in sorted(self.statics.items()):
            itemable_id = static_row.get("Itemable", {}).get("RowName")
            itemable_row = self.itemables.get(itemable_id)
            display_name = clean_display_text(itemable_row.get("DisplayName")) if itemable_row else None
            icon_path = normalize_item_icon_path(itemable_row.get("Icon")) if itemable_row else None
            label = self.overrides.get("itemLabels", {}).get(item_id) or display_name or item_id.replace("_", " ")
            self.items[item_id] = {
                "id": item_id,
                "label": label,
                "imagePath": icon_path or FALLBACK_IMAGE_PATH,
                "itemableId": itemable_id if itemable_id and itemable_id != "None" else None,
                "templateIds": sorted(templates_by_static.get(item_id, [])),
                "isPlaceholder": False,
                "isFood": is_food_item(static_row),
            }
            self._register_alias(item_id, item_id)
            self._register_alias(itemable_id if itemable_id != "None" else None, item_id)
            for template_id in templates_by_static.get(item_id, []):
                self._register_alias(template_id, item_id)

            if not itemable_row:
                self.diagnostics["missingItemableRows"].append({"itemId": item_id, "itemableId": itemable_id})
            if icon_path:
                disk_path = self.icons_dir / icon_path.removeprefix("/icarus-game/ItemIcons/")
                if not disk_path.exists():
                    self.diagnostics["missingIconFiles"].append({"itemId": item_id, "imagePath": icon_path})

    def _find_static_id(self, raw_id: str | None) -> str | None:
        if not raw_id or raw_id == "None":
            return None
        if raw_id in self.statics:
            return raw_id
        return self.statics_casefold.get(raw_id.casefold())

    def resolve_input(self, raw_id: str | None, recipe_id: str) -> str | None:
        return self._resolve(raw_id, recipe_id, prefer_template=False)

    def resolve_output(self, raw_id: str | None, recipe_id: str) -> str | None:
        return self._resolve(raw_id, recipe_id, prefer_template=True)

    def find_existing(self, raw_id: str | None, prefer_template: bool = False) -> str | None:
        resolvers = [self._resolve_template, self._find_static_id] if prefer_template else [self._find_static_id, self._resolve_template]
        for resolver in resolvers:
            item_id = resolver(raw_id)
            if item_id:
                return item_id
        return None

    def _resolve(self, raw_id: str | None, recipe_id: str, prefer_template: bool) -> str | None:
        if not raw_id or raw_id == "None":
            return None
        override_id = self.overrides.get("canonicalAliases", {}).get(raw_id)
        if override_id:
            static_id = self._find_static_id(override_id)
            if static_id:
                return static_id

        resolvers = [self._resolve_template, self._find_static_id] if prefer_template else [self._find_static_id, self._resolve_template]
        for resolver in resolvers:
            item_id = resolver(raw_id)
            if item_id:
                self._register_alias(raw_id, item_id)
                return item_id

        placeholder_id = raw_id
        if placeholder_id not in self.items:
            itemable_id = next(
                (
                    candidate
                    for candidate in (
                        self.itemables_casefold.get(raw_id.casefold()),
                        self.itemables_casefold.get(f"Item_{raw_id}".casefold()),
                    )
                    if candidate
                ),
                None,
            )
            itemable_row = self.itemables.get(itemable_id)
            display_name = clean_display_text(itemable_row.get("DisplayName")) if itemable_row else None
            icon_path = normalize_item_icon_path(itemable_row.get("Icon")) if itemable_row else None
            self.items[placeholder_id] = {
                "id": placeholder_id,
                "label": self.overrides.get("itemLabels", {}).get(placeholder_id) or display_name or placeholder_id.replace("_", " "),
                "imagePath": icon_path or FALLBACK_IMAGE_PATH,
                "itemableId": itemable_id,
                "templateIds": [],
                "isPlaceholder": True,
                "isFood": False,
            }
            if icon_path:
                disk_path = self.icons_dir / icon_path.removeprefix("/icarus-game/ItemIcons/")
                if not disk_path.exists():
                    self.diagnostics["missingIconFiles"].append({"itemId": placeholder_id, "imagePath": icon_path})
            self.diagnostics["placeholderItems"].append({"itemId": placeholder_id, "recipeIds": [recipe_id]})
        else:
            diagnostic = next(item for item in self.diagnostics["placeholderItems"] if item["itemId"] == placeholder_id)
            if recipe_id not in diagnostic["recipeIds"]:
                diagnostic["recipeIds"].append(recipe_id)
        self._register_alias(raw_id, placeholder_id)
        return placeholder_id

    def _resolve_template(self, raw_id: str | None) -> str | None:
        if not raw_id:
            return None
        template_id = raw_id if raw_id in self.templates else self.templates_casefold.get(raw_id.casefold())
        if not template_id:
            return None
        return self._find_static_id(self.templates[template_id].get("ItemStaticData", {}).get("RowName"))


def normalize_elements(
    values: list[dict[str, Any]],
    resolver: ItemResolver,
    recipe_id: str,
    output: bool,
) -> list[dict[str, Any]]:
    normalized = []
    for value in values:
        raw_id = value.get("Element", {}).get("RowName")
        item_id = resolver.resolve_output(raw_id, recipe_id) if output else resolver.resolve_input(raw_id, recipe_id)
        if item_id:
            normalized.append({"itemId": item_id, "quantity": value.get("Count", 1)})
    return normalized


def normalize_resources(values: list[dict[str, Any]], resolver: ItemResolver) -> list[dict[str, Any]]:
    normalized = []
    for value in values:
        item_id, units_per_quantity, quantity_unit = resolver.resolve_resource(value.get("Type", {}).get("Value"))
        if item_id:
            normalized.append(
                {
                    "itemId": item_id,
                    "quantity": value.get("RequiredUnits", 0) / units_per_quantity,
                    "quantityUnit": quantity_unit,
                }
            )
    return normalized


def build_catalog(
    data_dir: Path,
    icons_dir: Path,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides = overrides or {}
    source_tables = {
        "itemTemplates": load_table(data_dir / "D_ItemTemplate.json"),
        "itemsStatic": load_table(data_dir / "D_ItemsStatic.json"),
        "itemable": load_table(data_dir / "D_Itemable.json"),
        "recipeSets": load_table(data_dir / "D_RecipeSets.json", required=False),
    }
    recipe_tables = {
        source: load_table(data_dir / filename, required=source == "processor")
        for source, filename in RECIPE_TABLES
    }
    resolver = ItemResolver(
        source_tables["itemTemplates"].get("Rows", []),
        source_tables["itemsStatic"].get("Rows", []),
        source_tables["itemable"].get("Rows", []),
        icons_dir,
        overrides,
    )

    recipes_by_id: dict[str, dict[str, Any]] = {}
    recipe_ids_by_output: dict[str, list[str]] = defaultdict(list)
    recipe_ids_by_input: dict[str, list[str]] = defaultdict(list)
    duplicate_recipe_ids: list[str] = []

    for source, table in recipe_tables.items():
        for row in table.get("Rows", []):
            local_id = row.get("Name")
            if not local_id:
                continue
            recipe_id = f"{source}:{local_id}"
            if recipe_id in recipes_by_id:
                duplicate_recipe_ids.append(recipe_id)
                continue
            resource_inputs = normalize_resources(row.get("ResourceInputs", []), resolver)
            resource_outputs = normalize_resources(row.get("ResourceOutputs", []), resolver)
            inputs = normalize_elements(row.get("Inputs", []), resolver, recipe_id, output=False) + resource_inputs
            outputs = normalize_elements(row.get("Outputs", []), resolver, recipe_id, output=True) + resource_outputs
            recipe = {
                "id": recipe_id,
                "name": local_id,
                "source": source,
                "enabled": not row.get("bForceDisableRecipe", False),
                "inputs": inputs,
                "outputs": outputs,
                "recipeSetIds": sorted(
                    value.get("RowName") for value in row.get("RecipeSets", []) if value.get("RowName") not in (None, "None")
                ),
                "requiredMillijoules": row.get("RequiredMillijoules"),
                "resourceInputs": resource_inputs,
                "resourceOutputs": resource_outputs,
            }
            recipes_by_id[recipe_id] = recipe
            for value in inputs:
                recipe_ids_by_input[value["itemId"]].append(recipe_id)
            for value in outputs:
                recipe_ids_by_output[value["itemId"]].append(recipe_id)

    defaults: dict[str, str] = {}
    configured_defaults = overrides.get("defaultRecipes", {})
    for item_id, recipe_ids in sorted(recipe_ids_by_output.items()):
        configured = configured_defaults.get(item_id)
        if configured in recipe_ids:
            defaults[item_id] = configured
            continue
        enabled_ids = [recipe_id for recipe_id in recipe_ids if recipes_by_id[recipe_id]["enabled"]]
        candidates = enabled_ids or recipe_ids
        matching_ids = [
            recipe_id
            for recipe_id in candidates
            if recipes_by_id[recipe_id]["name"].casefold() in {item_id.casefold(), *(alias.casefold() for alias, target in resolver.aliases.items() if target == item_id)}
        ]
        defaults[item_id] = sorted(matching_ids or candidates, key=lambda value: (value.split(":", 1)[0] != "processor", value))[0]

    recipe_sets = {}
    for row in source_tables["recipeSets"].get("Rows", []):
        recipe_set_id = row.get("Name")
        if not recipe_set_id:
            continue
        item_id = resolver.find_existing(recipe_set_id)
        icon_path = normalize_item_icon_path(row.get("RecipeSetIcon"))
        recipe_sets[recipe_set_id] = {
            "id": recipe_set_id,
            "label": clean_display_text(row.get("RecipeSetName")) or recipe_set_id.replace("_", " "),
            "imagePath": resolver.items.get(item_id, {}).get("imagePath") or icon_path or FALLBACK_IMAGE_PATH,
            "itemId": item_id if item_id in resolver.statics else None,
        }

    diagnostics = {
        **{key: sorted(value, key=lambda item: json.dumps(item, sort_keys=True)) for key, value in resolver.diagnostics.items()},
        "duplicateRecipeIds": sorted(duplicate_recipe_ids),
        "itemsWithMultipleRecipes": sorted(
            {item_id: sorted(recipe_ids) for item_id, recipe_ids in recipe_ids_by_output.items() if len(recipe_ids) > 1}.items()
        ),
    }
    row_counts = {
        "D_ItemTemplate.json": len(source_tables["itemTemplates"].get("Rows", [])),
        "D_ItemsStatic.json": len(source_tables["itemsStatic"].get("Rows", [])),
        "D_Itemable.json": len(source_tables["itemable"].get("Rows", [])),
        "D_RecipeSets.json": len(source_tables["recipeSets"].get("Rows", [])),
        **{filename: len(recipe_tables[source].get("Rows", [])) for source, filename in RECIPE_TABLES},
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "sourceRowCounts": row_counts,
        "itemsById": dict(sorted(resolver.items.items())),
        "itemIdByAlias": dict(sorted(resolver.aliases.items())),
        "recipesById": dict(sorted(recipes_by_id.items())),
        "recipeIdsByOutputItemId": {key: sorted(value) for key, value in sorted(recipe_ids_by_output.items())},
        "recipeIdsByInputItemId": {key: sorted(value) for key, value in sorted(recipe_ids_by_input.items())},
        "defaultRecipeIdByOutputItemId": defaults,
        "recipeSetsById": dict(sorted(recipe_sets.items())),
        "diagnostics": diagnostics,
    }


def diagnostic_counts(catalog: dict[str, Any]) -> dict[str, int]:
    return {key: len(value) for key, value in catalog["diagnostics"].items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and audit the Icarus crafting catalog.")
    parser.add_argument("--data-dir", type=Path, default=Path("public/icarus-game/Data"))
    parser.add_argument("--icons-dir", type=Path, default=Path("public/icarus-game/ItemIcons"))
    parser.add_argument("--overrides", type=Path, default=Path("scripts/icarus_catalog_overrides.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    overrides = load_table(args.overrides, required=False) if args.overrides else {}
    catalog = build_catalog(args.data_dir, args.icons_dir, overrides)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    counts = diagnostic_counts(catalog)
    print(json.dumps({"sourceRowCounts": catalog["sourceRowCounts"], "diagnostics": counts}, indent=2, sort_keys=True))
    strict_failures = counts["duplicateRecipeIds"] + counts["missingIconFiles"] + counts["placeholderItems"]
    if args.strict and strict_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()