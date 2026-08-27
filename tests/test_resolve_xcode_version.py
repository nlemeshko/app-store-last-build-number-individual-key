import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "resolve_xcode_version.py"
SPEC = importlib.util.spec_from_file_location("resolve_xcode_version", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ParseMarketingVersionTests(unittest.TestCase):
    def test_parses_target_marketing_version(self):
        output = """
            BUILD_DIR = /tmp/build
            MARKETING_VERSION = 3.2.0
            PRODUCT_NAME = Monix
        """

        self.assertEqual(MODULE.parse_marketing_version(output), "3.2.0")

    def test_accepts_repeated_identical_values(self):
        output = "MARKETING_VERSION = 3.2.0\nMARKETING_VERSION = 3.2.0\n"

        self.assertEqual(MODULE.parse_marketing_version(output), "3.2.0")

    def test_rejects_conflicting_values(self):
        output = "MARKETING_VERSION = 1.0.0\nMARKETING_VERSION = 3.2.0\n"

        with self.assertRaisesRegex(ValueError, "Conflicting"):
            MODULE.parse_marketing_version(output)

    def test_rejects_unresolved_value(self):
        with self.assertRaisesRegex(ValueError, "not fully resolved"):
            MODULE.parse_marketing_version("MARKETING_VERSION = $(APP_VERSION)\n")


class ResolveDirectProjectVersionTests(unittest.TestCase):
    def test_resolves_version_for_named_target_and_configuration(self):
        objects = {
            "TARGET": {
                "isa": "PBXNativeTarget",
                "name": "Monix",
                "buildConfigurationList": "CONFIG_LIST",
            },
            "CONFIG_LIST": {
                "isa": "XCConfigurationList",
                "buildConfigurations": ["DEBUG", "RELEASE"],
            },
            "DEBUG": {
                "isa": "XCBuildConfiguration",
                "name": "Debug",
                "buildSettings": {"MARKETING_VERSION": "3.1.0"},
            },
            "RELEASE": {
                "isa": "XCBuildConfiguration",
                "name": "Release",
                "buildSettings": {"MARKETING_VERSION": "3.2.0"},
            },
            "EXTENSION": {
                "isa": "PBXNativeTarget",
                "name": "MONIXWUIExt",
                "buildConfigurationList": "EXTENSION_CONFIG_LIST",
            },
            "EXTENSION_CONFIG_LIST": {
                "isa": "XCConfigurationList",
                "buildConfigurations": ["EXTENSION_RELEASE"],
            },
            "EXTENSION_RELEASE": {
                "isa": "XCBuildConfiguration",
                "name": "Release",
                "buildSettings": {"MARKETING_VERSION": "1.0.0"},
            },
        }

        version = MODULE.resolve_direct_project_version(objects, "Monix", "Release")

        self.assertEqual(version, "3.2.0")

    def test_returns_none_for_inherited_version(self):
        objects = {
            "TARGET": {
                "isa": "PBXNativeTarget",
                "name": "Monix",
                "buildConfigurationList": "CONFIG_LIST",
            },
            "CONFIG_LIST": {"buildConfigurations": ["RELEASE"]},
            "RELEASE": {
                "name": "Release",
                "buildSettings": {"MARKETING_VERSION": "$(APP_VERSION)"},
            },
        }

        version = MODULE.resolve_direct_project_version(objects, "Monix", "Release")

        self.assertIsNone(version)


class FindProjectTests(unittest.TestCase):
    def test_validates_explicit_project(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "Monix.xcodeproj"
            project.mkdir()

            self.assertEqual(MODULE.find_project(str(project)), project)


if __name__ == "__main__":
    unittest.main()
