"""Public career paths must not hide local-path or private-key disclosures."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("release_check", Path(__file__).resolve().parents[1] / "scripts/verify_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleasePrivacyTests(unittest.TestCase):
    def test_public_careers_path_is_not_a_local_binding(self):
        self.assertFalse(release.has_private_binding('"https://www.cadence.com/en_US/home/company/life-at-cadence/careers.html"'))

    def test_web_url_does_not_hide_private_material(self):
        private = "/" + "Users" + "/" + "private-person" + "/resume.pdf"
        key = "-----BEGIN " + "PRIVATE KEY-----"
        for value in (private, '"' + private + '"', "file://" + private,
                      "https://example.invalid/?path=" + private,
                      "https://example.invalid/#" + private,
                      "https://example.invalid/ " + private,
                      "[link](https://example.invalid/)" + private,
                      r"https://example.invalid/x\n" + private,
                      "https://" + private,
                      "https://[invalid" + private,
                      "https://example.invalid/" + key):
            with self.subTest(value=value):
                self.assertTrue(release.has_private_binding(value))


class ReleaseInventoryTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = self.root / release.INVENTORY
        self.manifest.parent.mkdir(parents=True)
        (self.root / 'README.md').write_text('fictional release')
        self.manifest.write_text(release.INVENTORY + '\nREADME.md\n')

    def test_only_reviewed_files_are_accepted(self):
        self.assertEqual(len(release.files(self.root)), 2)
        for name in ('.env', 'resume.pdf', 'notes.txt', '__pycache__/private.json'):
            path = self.root / name
            path.parent.mkdir(exist_ok=True)
            path.write_text('fictional private input')
            with self.assertRaisesRegex(ValueError, 'unreviewed'):
                release.files(self.root)
            path.unlink()

    def test_generated_cache_is_not_exported(self):
        cache = self.root / '__pycache__/module.cpython-313.pyc'
        cache.parent.mkdir()
        cache.write_bytes(b'normal generated cache')
        self.assertNotIn(cache, release.files(self.root))

    def test_symlinks_and_unsafe_inventory_fail(self):
        link = self.root / 'extra'
        link.symlink_to(self.root / 'README.md')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            release.files(self.root)
        link.unlink()
        self.manifest.write_text('../outside\n')
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            release.files(self.root)

    def test_toolkit_accepts_cache_but_rejects_unknown_files(self):
        import tempfile
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('toolkit_check', Path(__file__).resolve().parents[1] / 'toolkit/verify_offline.py')
        toolkit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(toolkit)
        source = self.root / 'toolkit'
        source.mkdir()
        (source / 'SHAREABLE_FILES.txt').write_text('SHAREABLE_FILES.txt\nmodule.py\n')
        (source / 'module.py').write_text('pass\n')
        cache = source / '__pycache__/module.cpython-313.pyc'
        cache.parent.mkdir()
        cache.write_bytes(b'generated cache')
        with tempfile.TemporaryDirectory() as directory, patch.object(toolkit, 'ROOT', source):
            copied = toolkit.copy_package(Path(directory) / 'clean')
            self.assertFalse((copied / '__pycache__').exists())
            (source / '.env').write_text('fictional')
            with self.assertRaisesRegex(ValueError, 'inventory'):
                toolkit.copy_package(Path(directory) / 'rejected')
