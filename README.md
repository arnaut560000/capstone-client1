# OSY Connect - Python desktop app

A native **Tkinter + SQLite** Out-of-School Youth Monitoring System. Runs without XAMPP, MySQL, a browser, or a web server.

## Open the Windows app

Double-click the **OSY Connect** shortcut on your desktop, or open **`OSY Connect.exe`** in this project folder. No terminal, Python installation, XAMPP, or internet connection is needed for the packaged app. Allow a few seconds for it to open.

The GitHub repository contains the source code and build script. Generated executables and desktop shortcuts are not tracked. If you downloaded the source from GitHub, use the Python command below or follow **Rebuild the Windows executable** to create your own `.exe` and shortcut.

The executable uses the existing `desktop-data` folder beside it, so the Python and executable versions share the same records and administrator account. Keep the executable in this folder so the desktop shortcut continues to work.

## Start with one command

This is an alternative for running the Python source; the Windows executable above is already self-contained.

Install **Python 3.10 or newer** from python.org, including Tcl/Tk and pip (included with the standard Windows installer). Open a terminal in this project folder and run:

```powershell
python main.py
```

The launcher checks that photo and PDF support actually work. On Windows it installs Pillow and ReportLab under `%LOCALAPPDATA%\OSYConnect\runtime`, outside OneDrive and the project folder. Incomplete installations are repaired by installing into a fresh folder; existing dependency folders are never overwritten or deleted. Installation or repair needs internet access; healthy installations run offline. No administrator permission is needed when the project and local app-data folders are writable. Old `.desktop-deps` folders are no longer used.

On first launch, create your own administrator username and password. The app automatically creates `desktop-data/osy.sqlite3`. No database import is required for a fresh installation. There are no default passwords or sample records in your real database.

## Features

- Administrator setup, login, logout, salted password hashing, and temporary login lockout.
- Dashboard totals, age groups, employment counts, and recent registrations.
- Register and edit personal, education, employment, and registration details.
- Automatically calculated age and sequential IDs such as `OSY-2026-0001`. The ID year uses the current year, matching the original app. Editing a record preserves its ID.
- Optional JPG, PNG, or WebP photos, up to 2 MB.
- Search by name or OSY ID; filter by sex, status, and employment.
- Full profiles, reversible archiving, and restoration.
- ID preview and **86 × 54 mm PDF ID cards**. Open the exported PDF in a PDF viewer and print at Actual size / 100%.
- Filtered **A4 landscape PDF reports** and CSV exports. Every matching record is exported, including records outside the visible rows.
- Organization name settings, complete ZIP backups, and CSV migration from the old system.

## Use another PC

Copy **`OSY Connect.exe`** into a writable folder on another 64-bit Windows PC and double-click it. Python and XAMPP are not required. A fresh installation creates its database and asks you to create an administrator account.

For the source-code version instead, copy `main.py`, `requirements.txt`, and the `desktop` folder, install Python, and run `python main.py`.

To keep the existing records and account, close the app and also copy the complete **`desktop-data` folder**, or restore a backup as described below. The SQLite database and photos travel together. A separate installation has separate records; there is no automatic synchronization. Keep the working database on a local disk; do not synchronize an actively open SQLite database through OneDrive or a shared folder. Copy closed backups instead.

If the project is in OneDrive, you can move the project to a normal local folder, or override only the data location before launching:

```powershell
$env:OSY_DATA_DIR = "$env:LOCALAPPDATA\OSYConnect"
python main.py
```

## Bring records over from XAMPP

The original PHP database is **not changed or imported automatically**. Export once while the old MySQL service is available:

1. In phpMyAdmin, open the existing `osy_monitoring` database and select **`osy_records`**.
2. Export the table as **CSV**, using UTF-8, a comma separator, double-quote enclosure, and the option to put **column names in the first row**. Do not select SQL format. Include archived records if you want to keep them.
3. In the desktop app, open **Data & backups → Import records CSV** and choose the file.
4. If you have profile photos, select the old project's **`storage/photos`** folder when asked.

Required CSV columns: `osy_id`, `full_name`, `birthdate`, `sex`, `address`, `contact_number`, `educational_attainment`, `last_school`, `reason_stopped`, `employment_status`, `date_registered`, `status`. Optional columns: `photo`, `archived_at`. Other columns are ignored. Dates must be `YYYY-MM-DD`. The app's own CSV exports also use this format.

Original OSY IDs and archive status are retained, and the next ID is adjusted to avoid collisions. Invalid rows or duplicate IDs cancel the entire import. Missing photos are reported after import; those records use initials. Old MySQL administrator passwords are not imported: use the new account you create in the desktop app. Import timestamps become the desktop creation/update timestamps.

## Back up and restore

Choose **Data & backups → Create backup ZIP**. The ZIP includes the SQLite database (records, account, settings, ID counters) and referenced photos.

To restore or move to another PC:

1. Close OSY Connect on the destination PC.
2. Preserve its existing `desktop-data` folder by renaming it as a backup.
3. Create a new `desktop-data` folder and extract the ZIP contents into it. `osy.sqlite3` must be directly inside `desktop-data`, with photos in `desktop-data/photos`.
4. Open `OSY Connect.exe` (or run `python main.py`) and use the administrator login from the restored backup.

If `OSY_DATA_DIR` is set, restore to that folder instead. Login controls the application interface; the database and backups are not encrypted. Protect access to the data files.

## Rebuild the Windows executable

Developers can rebuild the executable after changing the Python code. This requires Python and internet access for build dependencies:

```powershell
.\build_windows.ps1 -CreateShortcut
```

The script creates an isolated build environment under local app-data, uses PyInstaller to bundle the complete app into one executable, tests that executable with disposable data, then copies it to `OSY Connect.exe` beside the existing database folder. `-CreateShortcut` creates or updates the desktop shortcut. Close the executable before rebuilding. The build never bundles your records or modifies your database.

The packaged self-test covers SQLite, authentication, photos, Tkinter, ID and report PDFs, and backups. Results are saved under `build/packaged-check-*.json`.

## Verification

After the first launch has installed dependencies:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests use disposable data and cover authentication, validation, persistent records, concurrent ID allocation, search/filtering, archive/restore, photos, backup recovery, CSV migration/rollback, PDF exports, and the Tkinter workflow. The interface test briefly creates windows and requires a graphical desktop.

## Project layout

- `main.py`: one-command launcher and first-run dependency setup.
- `desktop/data.py`: SQLite storage, validation, authentication, migration, backups.
- `desktop/ui.py`: Tkinter screens and record editor.
- `desktop/printing.py`: PDF ID cards and reports.
- `desktop-data/`: automatically created database and photos; preserve this folder.
- `tests/test_desktop.py`: desktop tests.

The previous PHP files remain available as a fallback. Their original instructions are in [README-PHP.md](README-PHP.md); they are not used by the desktop application.
