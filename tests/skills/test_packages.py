"""Deterministic package tests, not simulated semantic job-fit tests."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("skill_packages", ROOT / "scripts/validate_skills.py")
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)


class IsolatedPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def copy(self, name="job-search"):
        return Path(shutil.copytree(ROOT / ".agents/skills" / name, self.root / name))

    def test_each_skill_survives_individual_installation(self):
        for name in packages.NAMES:
            with self.subTest(skill=name):
                self.assertEqual(packages.validate_package(self.copy(name)), [])

    def test_missing_bundled_reference_is_detected(self):
        package = self.copy()
        (package / "references/posting-verification.md").unlink()
        self.assertTrue(any("missing reference" in x for x in packages.validate_package(package)))

    def test_repository_sibling_cannot_mask_external_dependency(self):
        package = self.copy()
        (self.root / "shared.md").write_text("fictional sibling")
        with (package / "SKILL.md").open("a") as handle:
            handle.write("\n[dependency](../shared.md)\n")
        self.assertTrue(any("escapes package" in x for x in packages.validate_package(package)))

    def test_encoded_escape_is_detected(self):
        package = self.copy()
        with (package / "SKILL.md").open("a") as handle:
            handle.write("\n[dependency](%2e%2e/shared.md)\n")
        self.assertTrue(any("escapes package" in x for x in packages.validate_package(package)))

    def test_symlink_to_private_input_is_rejected(self):
        package = self.copy()
        private = self.root / "private-resume.md"
        private.write_text("fictional personal input")
        (package / "resume.md").symlink_to(private)
        self.assertTrue(any("symlink" in x for x in packages.validate_package(package)))

    def test_accidental_binary_input_is_not_a_package_asset(self):
        package = self.copy()
        (package / "resume.pdf").write_bytes(b"fictional")
        self.assertTrue(any("unreviewed" in x for x in packages.validate_package(package)))

    def test_renamed_directory_cannot_claim_original_skill_name(self):
        package = self.copy()
        renamed = package.rename(self.root / "different-name")
        self.assertTrue(any("does not match" in x for x in packages.validate_package(renamed)))

    def test_release_privacy_scan_includes_yaml_preferences(self):
        release_spec = importlib.util.spec_from_file_location(
            "skill_release", ROOT / "Application Workflow/support/scripts/verify_release.py")
        release = importlib.util.module_from_spec(release_spec)
        release_spec.loader.exec_module(release)
        private_path = "/" + "Users" + "/" + "private-person" + "/resume.pdf"
        for suffix in (".yaml", ".yml"):
            with self.subTest(suffix=suffix):
                source = self.root / ("preferences" + suffix)
                source.write_text("resume_path: " + private_path + "\n")
                errors = StringIO()
                with patch.object(release, "REPO_ROOT", self.root), \
                     patch.object(release, "files", return_value=[source]), \
                     patch.object(release, "workbook_check"), redirect_stderr(errors):
                    self.assertEqual(release.main(), 1)
                self.assertIn("private binding", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
