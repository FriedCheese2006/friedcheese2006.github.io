import json
import tempfile
import unittest
from pathlib import Path

from scripts.icarus_catalog import FALLBACK_IMAGE_PATH, build_catalog, normalize_item_icon_path


class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "Data"
        self.icons_dir = self.root / "ItemIcons"
        self.data_dir.mkdir()
        (self.icons_dir / "Resources").mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_table(self, name, rows):
        (self.data_dir / name).write_text(json.dumps({"Rows": rows}), encoding="utf-8")

    def write_base_tables(self):
        self.write_table(
            "D_ItemTemplate.json",
            [
                {"Name": "Iron_Ingot", "ItemStaticData": {"RowName": "Refined_Metal"}},
                {"Name": "Iron_Ore", "ItemStaticData": {"RowName": "Metal_Ore"}},
            ],
        )
        self.write_table(
            "D_ItemsStatic.json",
            [
                {"Name": "Refined_Metal", "Itemable": {"RowName": "Item_Iron_Ingot"}},
                {"Name": "Metal_Ore", "Itemable": {"RowName": "Item_Iron_Ore"}},
            ],
        )
        self.write_table(
            "D_Itemable.json",
            [
                {
                    "Name": "Item_Iron_Ingot",
                    "DisplayName": 'NSLOCTEXT("Items", "Iron", "Iron Ingot")',
                    "Icon": "/Game/Assets/2DArt/UI/Items/Item_Icons/Resources/ITEM_Iron_Ingot.ITEM_Iron_Ingot",
                },
                {
                    "Name": "Item_Iron_Ore",
                    "DisplayName": 'NSLOCTEXT("Items", "Ore", "Iron Ore")',
                    "Icon": "/Game/Assets/2DArt/UI/Items/Item_Icons/Resources/ITEM_Iron_Ore.ITEM_Iron_Ore",
                },
            ],
        )
        (self.icons_dir / "Resources" / "ITEM_Iron_Ingot.png").touch()
        (self.icons_dir / "Resources" / "ITEM_Iron_Ore.png").touch()

    def test_catalog_preserves_multiple_recipes_for_canonical_output(self):
        self.write_base_tables()
        self.write_table(
            "D_ProcessorRecipes.json",
            [
                {
                    "Name": "Iron_Ingot",
                    "Inputs": [{"Element": {"RowName": "Metal_Ore"}, "Count": 2}],
                    "Outputs": [{"Element": {"RowName": "Iron_Ingot"}, "Count": 1}],
                },
                {
                    "Name": "Iron_Ingot_Alternative",
                    "Inputs": [{"Element": {"RowName": "metal_ore"}, "Count": 3}],
                    "Outputs": [{"Element": {"RowName": "Iron_Ingot"}, "Count": 2}],
                },
            ],
        )

        catalog = build_catalog(self.data_dir, self.icons_dir)

        self.assertEqual(
            catalog["recipeIdsByOutputItemId"]["Refined_Metal"],
            ["processor:Iron_Ingot", "processor:Iron_Ingot_Alternative"],
        )
        self.assertEqual(catalog["defaultRecipeIdByOutputItemId"]["Refined_Metal"], "processor:Iron_Ingot")
        self.assertEqual(catalog["recipesById"]["processor:Iron_Ingot_Alternative"]["inputs"][0]["itemId"], "Metal_Ore")

    def test_food_classification_uses_canonical_static_item_tags(self):
        self.write_base_tables()
        static_table_path = self.data_dir / "D_ItemsStatic.json"
        static_rows = json.loads(static_table_path.read_text(encoding="utf-8"))["Rows"]
        static_rows[0]["Generated_Tags"] = {
            "GameplayTags": [{"TagName": "Item.Consumable.Food.Cooked.Meat"}]
        }
        static_rows.extend(
            [
                {"Name": "Beer", "Manual_Tags": {"GameplayTags": [{"TagName": "FieldGuide.Food"}]}},
                {"Name": "Cream", "Manual_Tags": {"GameplayTags": [{"TagName": "Item.Resource.Spoilable"}]}},
            ]
        )
        self.write_table("D_ItemsStatic.json", static_rows)
        self.write_table(
            "D_ProcessorRecipes.json",
            [
                {
                    "Name": "Iron_Ingot",
                    "Inputs": [{"Element": {"RowName": "Iron_Ore"}, "Count": 1}],
                    "Outputs": [{"Element": {"RowName": "Iron_Ingot"}, "Count": 1}],
                }
            ],
        )

        catalog = build_catalog(self.data_dir, self.icons_dir)

        self.assertTrue(catalog["itemsById"]["Refined_Metal"]["isFood"])
        self.assertTrue(catalog["itemsById"]["Beer"]["isFood"])
        self.assertTrue(catalog["itemsById"]["Cream"]["isFood"])
        self.assertFalse(catalog["itemsById"]["Metal_Ore"]["isFood"])
        self.assertEqual(catalog["recipesById"]["processor:Iron_Ingot"]["outputs"][0]["itemId"], "Refined_Metal")

    def test_extractor_recipe_and_placeholder_are_retained(self):
        self.write_base_tables()
        self.write_table("D_ProcessorRecipes.json", [])
        self.write_table(
            "D_ExtractorRecipes.json",
            [
                {
                    "Name": "Unknown_Extraction",
                    "Inputs": [{"Element": {"RowName": "Missing_Input"}, "Count": 1}],
                    "Outputs": [{"Element": {"RowName": "Iron_Ingot"}, "Count": 4}],
                    "RecipeSets": [{"RowName": "Extractor"}],
                }
            ],
        )

        catalog = build_catalog(self.data_dir, self.icons_dir)

        recipe = catalog["recipesById"]["extractor:Unknown_Extraction"]
        self.assertEqual(recipe["outputs"], [{"itemId": "Refined_Metal", "quantity": 4}])
        self.assertEqual(recipe["inputs"], [{"itemId": "Missing_Input", "quantity": 1}])
        self.assertEqual(catalog["itemsById"]["Missing_Input"]["imagePath"], FALLBACK_IMAGE_PATH)
        self.assertTrue(catalog["itemsById"]["Missing_Input"]["isPlaceholder"])

    def test_icon_paths_use_final_object_suffix_and_report_missing_file(self):
        self.write_base_tables()
        self.write_table("D_ProcessorRecipes.json", [])
        (self.icons_dir / "Resources" / "ITEM_Iron_Ore.png").unlink()

        catalog = build_catalog(self.data_dir, self.icons_dir)

        self.assertEqual(
            normalize_item_icon_path(
                "/Game/Assets/2DArt/UI/Items/Item_Icons/Resources/ITEM.Iron.ITEM.Iron"
            ),
            "/icarus-game/ItemIcons/Resources/ITEM.Iron.ITEM.Iron.png",
        )
        missing_ids = {item["itemId"] for item in catalog["diagnostics"]["missingIconFiles"]}
        self.assertEqual(missing_ids, {"Metal_Ore"})

    def test_recipe_set_without_static_item_does_not_create_placeholder(self):
        self.write_base_tables()
        self.write_table("D_ProcessorRecipes.json", [])
        self.write_table(
            "D_RecipeSets.json",
            [{"Name": "Character", "RecipeSetName": 'NSLOCTEXT("Sets", "Character", "Character")'}],
        )

        catalog = build_catalog(self.data_dir, self.icons_dir)

        self.assertEqual(catalog["recipeSetsById"]["Character"]["itemId"], None)
        self.assertNotIn("Character", catalog["itemsById"])
        self.assertEqual(catalog["diagnostics"]["placeholderItems"], [])

    def test_placeholder_uses_matching_itemable_metadata(self):
        self.write_base_tables()
        itemables = json.loads((self.data_dir / "D_Itemable.json").read_text(encoding="utf-8"))["Rows"]
        itemables.append(
            {
                "Name": "Item_Missing_Bench",
                "DisplayName": 'NSLOCTEXT("Items", "Bench", "Missing Bench")',
                "Icon": "/Game/Assets/2DArt/UI/Items/Item_Icons/Deployables/Missing_Bench.Missing_Bench",
            }
        )
        self.write_table("D_Itemable.json", itemables)
        (self.icons_dir / "Deployables").mkdir()
        (self.icons_dir / "Deployables" / "Missing_Bench.png").touch()
        self.write_table(
            "D_ProcessorRecipes.json",
            [
                {
                    "Name": "Missing_Bench",
                    "Inputs": [],
                    "Outputs": [{"Element": {"RowName": "Missing_Bench"}, "Count": 1}],
                }
            ],
        )

        catalog = build_catalog(self.data_dir, self.icons_dir)

        item = catalog["itemsById"]["Missing_Bench"]
        self.assertEqual(item["label"], "Missing Bench")
        self.assertEqual(item["imagePath"], "/icarus-game/ItemIcons/Deployables/Missing_Bench.png")
        self.assertTrue(item["isPlaceholder"])

    def test_resource_flows_become_catalog_items_and_recipe_edges(self):
        self.write_base_tables()
        self.write_table(
            "D_ProcessorRecipes.json",
            [
                {
                    "Name": "Oil_Iron",
                    "Inputs": [{"Element": {"RowName": "Metal_Ore"}, "Count": 2}],
                    "ResourceInputs": [{"Type": {"Value": "Refined_Oil"}, "RequiredUnits": 500}],
                    "Outputs": [{"Element": {"RowName": "Iron_Ingot"}, "Count": 1}],
                },
                {
                    "Name": "Oil_Output",
                    "Inputs": [],
                    "ResourceOutputs": [{"Type": {"Value": "Refined_Oil"}, "RequiredUnits": 250}],
                },
                {
                    "Name": "Milk_Output",
                    "Inputs": [],
                    "ResourceOutputs": [{"Type": {"Value": "Milk"}, "RequiredUnits": 500}],
                },
            ],
        )
        overrides = {
            "resourceTypes": {
                "Refined_Oil": {
                    "label": "Refined Oil",
                    "imagePath": "/icarus-game/Images/question-mark.png",
                    "quantityUnit": "L",
                    "unitsPerQuantity": 1000,
                },
                "Milk": {
                    "label": "Milk",
                    "imagePath": "/icarus-game/Images/question-mark.png",
                    "isFood": True,
                    "quantityUnit": "L",
                    "unitsPerQuantity": 1000,
                }
            }
        }

        catalog = build_catalog(self.data_dir, self.icons_dir, overrides)

        resource = catalog["itemsById"]["Refined_Oil"]
        self.assertTrue(resource["isResource"])
        self.assertFalse(resource["isFood"])
        self.assertEqual(resource["quantityUnit"], "L")
        self.assertTrue(catalog["itemsById"]["Milk"]["isFood"])
        self.assertEqual(
            catalog["recipesById"]["processor:Oil_Iron"]["inputs"][-1],
            {"itemId": "Refined_Oil", "quantity": 0.5, "quantityUnit": "L"},
        )
        self.assertEqual(catalog["recipeIdsByInputItemId"]["Refined_Oil"], ["processor:Oil_Iron"])
        self.assertEqual(catalog["recipeIdsByOutputItemId"]["Refined_Oil"], ["processor:Oil_Output"])


if __name__ == "__main__":
    unittest.main()