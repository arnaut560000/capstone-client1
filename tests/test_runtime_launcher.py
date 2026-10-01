"""Regression checks for missing dependencies and locked old installations."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cache = Path(self.temp.name) / "runtime"
        self.root_patch = patch.object(main, "runtime_root", return_value=self.cache)
        self.root_patch.start()
        self.path_patch = patch.object(sys, "path", sys.path.copy())
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def existing(self):
        folder = self.cache / "install-old"
        folder.mkdir(parents=True)
        (folder / ".ready").write_text("ready")
        (folder / "keep.txt").write_text("must not overwrite")
        return folder

    def test_probe_detects_reportlab_with_missing_lib(self):
        folder = Path(self.temp.name)
        for name, content in [("reportlab", ""), ("PIL", "Image = ImageOps = ImageTk = None")]:
            package = folder / name
            package.mkdir()
            (package / "__init__.py").write_text(content, encoding="utf-8")
        self.assertIn("No module named 'reportlab.lib'", main.dependency_error(folder))

    def test_healthy_dependencies_do_not_install(self):
        folder = self.existing()
        with patch.object(main, "dependency_error", return_value=None), patch.object(main.subprocess, "run") as run:
            self.assertEqual(main.ensure_dependencies(), folder)
            self.assertEqual(sys.path[0], str(folder))
            run.assert_not_called()

    def test_repair_never_overwrites_old_folder(self):
        old = self.existing()
        with patch.object(main, "dependency_error", side_effect=["Missing reportlab.lib", None]) as check:
            with patch.object(main.subprocess, "run") as run:
                fresh = main.ensure_dependencies()
            self.assertEqual(check.call_count, 2)
            command = run.call_args.args[0]
            self.assertNotIn("--upgrade", command)
            self.assertNotIn("--force-reinstall", command)
            self.assertEqual(command[command.index("--target") + 1], str(fresh))
            self.assertNotEqual(fresh, old)
            self.assertEqual(fresh.parent, self.cache)
            self.assertTrue((fresh / ".ready").is_file())
            self.assertEqual((old / "keep.txt").read_text(), "must not overwrite")

    def test_failed_install_does_not_publish_ready_marker(self):
        with patch.object(main, "dependency_error", return_value="Missing reportlab.lib"):
            with patch.object(main.subprocess, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "still unavailable after installation"):
                    main.ensure_dependencies()
            run.assert_called_once()
        self.assertEqual(list(self.cache.glob("install-*/.ready")), [])

    def test_failed_download_does_not_loop_and_retry_uses_new_folder(self):
        with patch.object(main.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "pip")) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                main.ensure_dependencies()
            run.assert_called_once()
        failed = next(self.cache.glob("install-*"))
        with patch.object(main, "dependency_error", return_value=None), patch.object(main.subprocess, "run"):
            fresh = main.ensure_dependencies()
        self.assertNotEqual(failed, fresh)
        self.assertFalse((failed / ".ready").exists())

    def test_old_project_dependency_folder_is_never_probed(self):
        with patch.object(main, "dependency_error", return_value=None) as probe, patch.object(main.subprocess, "run"):
            fresh = main.ensure_dependencies()
        probe.assert_called_once_with(fresh)
        self.assertNotIn(".desktop-deps", str(fresh))


class RuntimePathTests(unittest.TestCase):
    def test_windows_default_uses_local_app_data(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"LOCALAPPDATA": folder, "OSY_RUNTIME_DIR": ""}), patch.object(sys, "platform", "win32"):
                self.assertEqual(main.runtime_root().parent, Path(folder).resolve() / "OSYConnect" / "runtime")


if __name__ == "__main__":
    unittest.main()
