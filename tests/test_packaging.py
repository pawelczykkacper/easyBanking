"""Check metadata used by HACS when downloading a version."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PackagingTests(unittest.TestCase):
    def test_no_override_of_core_pyjwt(self):
        manifest = json.loads((ROOT / "custom_components/enable_banking/manifest.json").read_text())
        self.assertFalse(any(item.lower().startswith("pyjwt") for item in manifest.get("requirements", [])))

    def test_hacs_can_resolve_integration(self):
        hacs = json.loads((ROOT / "hacs.json").read_text())
        self.assertTrue(hacs["name"])
        self.assertFalse(hacs.get("content_in_root", False))
        self.assertFalse(hacs.get("zip_release", False))
        folders = [p for p in (ROOT / "custom_components").iterdir() if p.is_dir() and p.name != "__pycache__"]
        self.assertEqual([p.name for p in folders], ["enable_banking"])
        manifest = json.loads((folders[0] / "manifest.json").read_text())
        for key in ("domain", "documentation", "issue_tracker", "codeowners", "name", "version"):
            self.assertTrue(manifest[key], key)
        self.assertEqual(manifest["domain"], folders[0].name)
        self.assertTrue((folders[0] / "__init__.py").is_file())
        self.assertTrue((ROOT / "README.md").is_file())

if __name__ == "__main__":
    unittest.main()
