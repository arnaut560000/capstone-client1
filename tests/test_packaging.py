"""Ensure the executable opens persistent data beside itself, not its extraction folder."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class PackagedDataTests(unittest.TestCase):
    def test_executable_uses_database_beside_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "OSY Connect.exe"
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)):
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(main.data_directory(), Path(folder).resolve() / "desktop-data")

    def test_python_and_executable_share_records_when_in_same_folder(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "frozen", False, create=True):
                source_data = main.data_directory()
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(main.ROOT / "OSY Connect.exe")):
                self.assertEqual(main.data_directory(), source_data)

    def test_explicit_data_location_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"OSY_DATA_DIR": folder}), patch.object(sys, "frozen", True, create=True):
                self.assertEqual(main.data_directory(), Path(folder).resolve())


if __name__ == "__main__":
    unittest.main()
