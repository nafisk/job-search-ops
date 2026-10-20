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


class WorkbookPrivacyTests(unittest.TestCase):
    def package(self, modifications):
        import io
        import zipfile
        stream = io.BytesIO()
        with zipfile.ZipFile(release.WORKFLOW_ROOT / 'sheets/job-search-tracker.xlsx') as source:
            parts = {name: source.read(name) for name in source.namelist()}
        parts.update(modifications)
        with zipfile.ZipFile(stream, 'w') as target:
            for name, body in parts.items(): target.writestr(name, body)
        stream.seek(0)
        return zipfile.ZipFile(stream)

    def test_original_blank_template_has_no_hidden_remnants(self):
        with self.package({}) as package:
            release.workbook_privacy_check(package)

    def test_deleted_unused_shared_string_is_rejected_without_known_signature(self):
        text = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Fictional deleted private note</t></si></sst>'
        with self.package({'xl/sharedStrings.xml': text}) as package:
            with self.assertRaisesRegex(ValueError, 'unused shared strings'):
                release.workbook_privacy_check(package)

    def test_personal_metadata_and_external_relationships_are_rejected(self):
        cases = [
            ('docProps/core.xml', '<cp:coreProperties xmlns:cp="urn:core" xmlns:dc="urn:dc"><dc:creator>Fictional Private Person</dc:creator></cp:coreProperties>', 'metadata'),
            ('xl/worksheets/_rels/sheet1.xml.rels', '<Relationships><Relationship TargetMode="External" Target="https://example.invalid/private-document" /></Relationships>', 'external relationship'),
            ('docProps/custom.xml', '<Properties><property name="Private note">Fictional</property></Properties>', 'custom workbook'),
            ('xl/embeddings/private.bin', b'fictional embedded material', 'embedded'),
        ]
        for name, body, error in cases:
            with self.subTest(name=name), self.package({name: body}) as package:
                with self.assertRaisesRegex(ValueError, error):
                    release.workbook_privacy_check(package)

    def test_xml_attribute_entities_and_nonvisible_parts_are_scanned(self):
        # The privacy signature is assembled so the fixture itself is shareable.
        private = '/' + 'Users' + '/' + 'private-person' + '/resume.pdf'
        encoded = private.replace('/', '&#47;')
        with self.package({'xl/custom.xml': '<unused private="' + encoded + '" />'}) as package:
            with self.assertRaisesRegex(ValueError, 'private binding'):
                release.workbook_privacy_check(package)
        with self.package({'xl/custom.xml': '<unused><!-- fictional removed note --></unused>'}) as package:
            with self.assertRaisesRegex(ValueError, 'hidden XML'):
                release.workbook_privacy_check(package)

    def test_orphan_comment_with_private_author_and_note_is_rejected(self):
        comment = '<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><authors><author>Fictional Private Person</author></authors><commentList><comment ref="A1" authorId="0"><text><t>Fictional old referral note</t></text></comment></commentList></comments>'
        with self.package({'xl/comments1.xml': comment}) as package:
            with self.assertRaisesRegex(ValueError, 'part inventory'):
                release.workbook_privacy_check(package)

    def test_orphan_worksheet_cannot_make_deleted_shared_string_look_used(self):
        import zipfile
        import xml.etree.ElementTree as ET
        namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        with zipfile.ZipFile(release.WORKFLOW_ROOT / 'sheets/job-search-tracker.xlsx') as source:
            strings = ET.fromstring(source.read('xl/sharedStrings.xml'))
        index = len(strings)
        ET.SubElement(ET.SubElement(strings, '{' + namespace + '}si'), '{' + namespace + '}t').text = 'Fictional deleted private note'
        orphan = '<worksheet xmlns="' + namespace + '"><sheetData><row r="1"><c r="A1" t="s"><v>' + str(index) + '</v></c></row></sheetData></worksheet>'
        with self.package({'xl/sharedStrings.xml': ET.tostring(strings), 'xl/worksheets/sheet8.xml': orphan}) as package:
            with self.assertRaisesRegex(ValueError, 'part inventory'):
                release.workbook_privacy_check(package)
