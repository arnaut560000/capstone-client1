"""Executable smoke test; never opens or modifies the real database."""
from datetime import date
from pathlib import Path
import json
import sys
import tempfile
import traceback


def self_test(report, default_data):
    result = {"ok": False, "frozen": bool(getattr(sys, "frozen", False)),
              "executable": sys.executable, "default_data": str(default_data), "checks": []}
    try:
        from PIL import Image, ImageTk
        from .ui import Application
        from .printing import id_pdf, report_pdf
        with tempfile.TemporaryDirectory(prefix="osy-exe-check-") as temporary:
            folder = Path(temporary)
            app = Application(folder / "data")
            callback_errors = []
            app.report_callback_exception = lambda *args: callback_errors.append(str(args[1]))
            try:
                app.store.setup("qaadmin", "Disposable-Test-123", "Disposable-Test-123")
                app.username = app.store.login("qaadmin", "Disposable-Test-123")
                result["checks"].append("SQLite and password authentication")
                photo = folder / "photo.png"
                Image.new("RGB", (120, 160), "#14765b").save(photo)
                record_id = app.store.save(dict(full_name="Packaging Test", birthdate="2005-01-02", sex="Female",
                    address="Fictional test address", contact_number="", educational_attainment="College level",
                    last_school="", reason_stopped="", employment_status="Unemployed",
                    date_registered=date.today().isoformat(), status="Active"), photo_source=photo)
                record = app.store.get(record_id)
                result["checks"].append("Record and photo storage")
                app.unbind("<Return>")
                app.shell()
                app.profile(record_id)
                app.update()
                app.preview_id(record_id)
                app.update()
                result["checks"].append("Tkinter, Tcl/Tk, and image preview")
                id_pdf(record, folder / "id.pdf", "Test Community", app.store.photo_path(record["photo"]))
                report_pdf([record], folder / "report.pdf", "Test Community")
                for name in ("id.pdf", "report.pdf"):
                    if not (folder / name).read_bytes().startswith(b"%PDF-"):
                        raise RuntimeError(f"Invalid PDF: {name}")
                result["checks"].append("ReportLab ID and report PDFs")
                app.store.backup(folder / "backup.zip")
                result["checks"].append("Database and photo backup")
                app.after(400, app.quit)
                app.mainloop()
                if callback_errors:
                    raise RuntimeError("; ".join(callback_errors))
            finally:
                app.close()
        result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not result["ok"]:
        raise SystemExit(1)
