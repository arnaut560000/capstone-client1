"""Run OSY Connect with: python main.py (Python 3.10+)."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import sysconfig
import tempfile
import argparse

ROOT = Path(__file__).resolve().parent


# Test the actual imports and bundled PDF resources in a fresh interpreter.
# Finding just 'reportlab' does not mean that 'reportlab.lib' is installed.
# A subprocess also avoids caching partially imported packages before a repair.
DEPENDENCY_PROBE = """
import sys
from io import BytesIO
sys.path.insert(0, sys.argv[1])
from PIL import Image, ImageOps, ImageTk
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepInFrame
Image.new('RGB', (1, 1)).save(BytesIO(), format='PNG')
pdf = canvas.Canvas(BytesIO())
pdf.drawString(10, 10, 'OSY dependency check')
pdf.save()
"""


def dependency_error(dependencies):
    result = subprocess.run([sys.executable, "-I", "-c", DEPENDENCY_PROBE, str(dependencies)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        return details.splitlines()[-1] if details else f"Dependency check exited with code {result.returncode}."
    return None


def runtime_root():
    """Keep executable packages out of synced folders and sandbox-owned files."""
    if os.environ.get("OSY_RUNTIME_DIR"):
        base = Path(os.environ["OSY_RUNTIME_DIR"]).expanduser()
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "OSYConnect" / "runtime"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "osy-connect" / "runtime"
    identity = (sys.version + sysconfig.get_platform() + str(Path(sys.executable).resolve())).encode()
    key = hashlib.sha256(identity + (ROOT / "requirements.txt").read_bytes()).hexdigest()[:16]
    return base.resolve() / key


def ensure_dependencies():
    cache = runtime_root()
    cache.mkdir(parents=True, exist_ok=True)
    dependencies = None
    # A ready marker is written only after a successful installation AND probe.
    # Never replace/delete an old installation: Windows may have its DLLs locked,
    # or it may belong to a different account. Concurrent launches are safe too.
    candidates = []
    for folder in cache.glob("install-*"):
        try:
            marker = folder / ".ready"
            if marker.is_file():
                candidates.append((marker.stat().st_mtime_ns, folder))
        except OSError:
            continue
    for _, folder in sorted(candidates, reverse=True):
        if dependency_error(folder) is None:
            dependencies = folder
            break
    if dependencies is None:
        dependencies = Path(tempfile.mkdtemp(prefix="install-", dir=cache))
        print("Setting up photo/PDF support in your local app-data folder.", flush=True)
        print("Internet is needed for setup. Existing data and old dependency folders are unchanged.", flush=True)
        print(f"Installing to: {dependencies}", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                        "--no-cache-dir", "--target", str(dependencies),
                        "-r", str(ROOT / "requirements.txt")], check=True)
        problem = dependency_error(dependencies)
        if problem:
            raise RuntimeError(f"Photo/PDF support is still unavailable after installation: {problem}")
        (dependencies / ".ready").write_text("Verified for OSY Connect\n", encoding="ascii")
    sys.path.insert(0, str(dependencies))
    return dependencies


def data_directory():
    default = Path(sys.executable).parent / "desktop-data" if getattr(sys, "frozen", False) else ROOT / "desktop-data"
    return Path(os.environ.get("OSY_DATA_DIR", str(default))).expanduser().resolve()


def main():
    parser = argparse.ArgumentParser(description="OSY Connect desktop application")
    parser.add_argument("--self-test", metavar="REPORT_JSON", help="Check the packaged app with disposable data and exit")
    arguments = parser.parse_args()
    if not getattr(sys, "frozen", False):
        ensure_dependencies()
    if arguments.self_test:
        from desktop.diagnostics import self_test
        self_test(Path(arguments.self_test), data_directory())
        return
    from desktop.ui import Application
    app = Application(data_directory())
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        import traceback
        message = f"Cannot start OSY Connect: {error}"
        if getattr(sys, "frozen", False):
            # A windowed executable has no terminal, so failures need a dialog.
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("OSY Connect could not start", message + "\n\nMake sure the app's folder is writable.", parent=root)
            root.destroy()
        else:
            traceback.print_exc()
            print(message, file=sys.stderr)
        sys.exit(1)
