"""Run with python -m unittest discover -s tests -p test_desktop.py -v.

All tests use temporary databases; the user's records are never touched.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import ensure_dependencies
ensure_dependencies()
from desktop.data import Store, export_csv
from desktop.printing import id_pdf, report_pdf
from PIL import Image


def sample(**overrides):
    return dict(full_name="María Test Youth", birthdate="2006-03-14", sex="Female",
                address="12 Sample Street, Test Community", contact_number="09123456789",
                educational_attainment="Junior high school graduate", last_school="Example School",
                reason_stopped="Example only", employment_status="Unemployed",
                date_registered=date.today().isoformat(), status="Active") | overrides


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.store = Store(self.folder / "data")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_setup_login_and_password_is_hashed(self):
        self.assertFalse(self.store.is_ready())
        self.store.setup("admin", "test-password-123", "test-password-123")
        self.assertEqual(self.store.login("admin", "test-password-123"), "admin")
        encoded = self.store.db.execute("SELECT password_hash FROM admins").fetchone()[0]
        self.assertNotIn("test-password", encoded)
        with self.assertRaises(ValueError):
            self.store.login("admin", "wrong")
        with self.assertRaises(ValueError):
            self.store.setup("other", "test-password-123", "test-password-123")

    def test_login_throttle_survives_reopen(self):
        self.store.setup("admin", "test-password-123", "test-password-123")
        for _ in range(5):
            with self.assertRaises(ValueError):
                self.store.login("admin", "wrong")
        self.store.close()
        self.store = Store(self.folder / "data")
        with self.assertRaisesRegex(ValueError, "wait one minute"):
            self.store.login("admin", "test-password-123")

    def test_validation_and_no_partial_insert(self):
        for values in (sample(full_name=""), sample(birthdate="2099-01-01"), sample(birthdate="2026-02-30"),
                       sample(sex="Invalid"), sample(address="x" * 501), sample(contact_number="abc"),
                       sample(date_registered="2000-01-01"), sample(educational_attainment="invalid")):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.store.save(values)
        self.assertEqual(self.store.records(), [])

    def test_persistence_and_stable_ids(self):
        first = self.store.save(sample())
        second = self.store.save(sample(full_name="Second Youth"))
        self.assertEqual(self.store.get(first)["osy_id"], f"OSY-{date.today().year}-0001")
        self.assertEqual(self.store.get(second)["osy_id"], f"OSY-{date.today().year}-0002")
        self.store.save(sample(full_name="Updated Youth"), first)
        self.store.close()
        self.store = Store(self.folder / "data")
        self.assertEqual(self.store.get(first)["full_name"], "Updated Youth")
        self.assertEqual(self.store.get(first)["osy_id"], f"OSY-{date.today().year}-0001")

    def test_concurrent_registration_ids(self):
        def register(index):
            connection = Store(self.folder / "data")
            try:
                return connection.get(connection.save(sample(full_name=f"Youth {index}")))["osy_id"]
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            identifiers = list(pool.map(register, range(12)))
        self.assertEqual(len(set(identifiers)), 12)
        self.assertEqual(sorted(int(value.split("-")[-1]) for value in identifiers), list(range(1, 13)))

    def test_archive_restore_search_and_filters(self):
        first = self.store.save(sample(full_name="Ana_100%"))
        self.store.save(sample(full_name="Other Youth", sex="Male", status="Inactive", employment_status="Employed"))
        self.assertEqual(len(self.store.records("_100%")), 1)
        self.assertEqual(len(self.store.records(sex="Male", status="Inactive", employment_status="Employed")), 1)
        self.assertEqual(self.store.records("' OR 1=1 --"), [])
        self.store.archive(first)
        self.assertEqual(len(self.store.records()), 1)
        self.assertEqual(len(self.store.records(archived=True)), 1)
        self.store.archive(first, False)
        self.assertEqual(len(self.store.records()), 2)

    def test_photos_backup_and_recovery(self):
        source = self.folder / "test.png"
        Image.new("RGB", (150, 200), "green").save(source)
        self.store.setup("admin", "test-password-123", "test-password-123")
        self.store.set_organization("Test Community")
        record_id = self.store.save(sample(), photo_source=source)
        record = self.store.get(record_id)
        self.assertTrue(self.store.photo_path(record["photo"]).is_file())
        self.assertIsNone(self.store.photo_path("../osy.sqlite3"))
        backup = self.folder / "backup.zip"
        self.store.backup(backup)
        restored_folder = self.folder / "restored"
        with zipfile.ZipFile(backup) as archive:
            archive.extractall(restored_folder)
        restored = Store(restored_folder)
        try:
            self.assertEqual(restored.login("admin", "test-password-123"), "admin")
            self.assertEqual(restored.organization(), "Test Community")
            self.assertTrue(restored.photo_path(restored.get(record_id)["photo"]).is_file())
        finally:
            restored.close()
        self.store.save(sample(), record_id, remove_photo=True)
        self.assertIsNone(self.store.get(record_id)["photo"])

    def test_bad_photo_does_not_create_record(self):
        source = self.folder / "bad.jpg"
        source.write_text("This is not an image")
        with self.assertRaises(OSError):
            self.store.save(sample(), photo_source=source)
        self.assertEqual(self.store.records(), [])

    def write_csv(self, rows):
        path = self.folder / "import.csv"
        export_csv(rows, path)
        return path

    def test_import_preserves_ids_archives_and_advances_sequence(self):
        path = self.write_csv([sample() | {"osy_id": f"OSY-{date.today().year}-0042", "archived_at": "2026-01-01 10:00:00"}])
        self.assertEqual(self.store.import_csv(path), (1, 0))
        self.assertEqual(len(self.store.records(archived=True)), 1)
        new_id = self.store.save(sample(full_name="Next youth"))
        self.assertEqual(self.store.get(new_id)["osy_id"], f"OSY-{date.today().year}-0043")
        with self.assertRaisesRegex(ValueError, "No records were imported"):
            self.store.import_csv(path)

    def test_import_invalid_second_row_rolls_back_records_photos_sequence(self):
        photos = self.folder / "old-photos"
        photos.mkdir()
        Image.new("RGB", (50, 50)).save(photos / "test.png")
        path = self.write_csv([sample() | {"osy_id": f"OSY-{date.today().year}-0050", "photo": "test.png"},
                               sample(birthdate="bad") | {"osy_id": f"OSY-{date.today().year}-0051"}])
        with self.assertRaisesRegex(ValueError, "row 3"):
            self.store.import_csv(path, photos)
        self.assertEqual(self.store.records(), [])
        self.assertEqual(list(self.store.photos.iterdir()), [])
        self.assertEqual(self.store.get(self.store.save(sample()))["osy_id"], f"OSY-{date.today().year}-0001")

    def test_import_missing_headers_and_unsafe_photo(self):
        path = self.folder / "bad.csv"
        path.write_text("name\nTest\n")
        with self.assertRaisesRegex(ValueError, "column headers"):
            self.store.import_csv(path)
        path = self.write_csv([sample() | {"osy_id": "OSY-2026-0001", "photo": "../secret.jpg"}])
        with self.assertRaisesRegex(ValueError, "filename only"):
            self.store.import_csv(path)

    def test_csv_roundtrip_unicode_newlines_and_quotes(self):
        original = sample(address='Line one, "quoted"\nSecond line')
        self.store.save(original)
        path = self.write_csv(self.store.records())
        target = Store(self.folder / "imported")
        try:
            target.import_csv(path)
            self.assertEqual(target.records()[0]["address"], original["address"])
            self.assertEqual(target.records()[0]["full_name"], original["full_name"])
        finally:
            target.close()

    def test_pdf_exports_long_fields_and_multi_page(self):
        record_id = self.store.save(sample(full_name="María " * 24, address="Long sample address. " * 23))
        record = self.store.get(record_id)
        card = self.folder / "card.pdf"
        report = self.folder / "report.pdf"
        empty = self.folder / "empty.pdf"
        id_pdf(record, card, "Community " * 12)
        report_pdf([record] * 65, report, "Test Community", "Filtered master list")
        report_pdf([], empty, "Test Community")
        for path in (card, report, empty):
            self.assertTrue(path.read_bytes().startswith(b"%PDF-"))
            self.assertGreater(path.stat().st_size, 500)

    def test_tkinter_workflow(self):
        from desktop.ui import Application
        application = Application(self.folder / "ui-data")
        errors = []
        application.report_callback_exception = lambda *args: errors.append(args)
        try:
            application.update()
            application.auth_vars["username"].set("testadmin")
            application.auth_vars["password"].set("test-password-123")
            application.auth_vars["confirm"].set("test-password-123")
            application.auth_submit()
            application.update()
            self.assertEqual(application.username, "testadmin")
            application.edit_record()
            editor = application.editor
            for key, value in sample().items():
                if key in editor.variables:
                    editor.variables[key].set(value)
                else:
                    editor.texts[key].delete("1.0", "end")
                    editor.texts[key].insert("1.0", value)
            editor.save()
            application.update()
            record_id = application.store.records()[0]["id"]
            application.records_page()
            application.update()
            self.assertEqual(len(application.tree.get_children()), 1)
            application.profile(record_id)
            application.preview_id(record_id)
            application.update()
            for child in application.winfo_children():
                if child.winfo_class() == "Toplevel":
                    child.destroy()
            application.data_page()
            application.update()
            application.logout()
            application.update()
            self.assertIsNone(application.username)
            self.assertNotIn("confirm", application.auth_vars)
            self.assertEqual(errors, [])
        finally:
            application.close()


if __name__ == "__main__":
    unittest.main()
