"""Local persistence, validation, password hashing, and portable backups."""
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
import csv
import hashlib
import hmac
import re
import secrets
import sqlite3
import tempfile
import zipfile

EDUCATION = ("No formal education", "Elementary level", "Elementary graduate", "Junior high school level",
             "Junior high school graduate", "Senior high school level", "Senior high school graduate",
             "Vocational / Technical", "College level", "College graduate")
CHOICES = {"sex": ("Male", "Female"), "educational_attainment": EDUCATION,
           "employment_status": ("Unemployed", "Employed"), "status": ("Active", "Inactive")}
LABELS = {"full_name": "Full name", "birthdate": "Birthdate", "sex": "Sex", "address": "Complete address",
          "contact_number": "Contact number", "educational_attainment": "Educational attainment",
          "last_school": "Last school attended", "reason_stopped": "Reason for stopping school",
          "employment_status": "Employment status", "date_registered": "Date registered", "status": "Record status"}
FIELDS = tuple(LABELS)
CSV_FIELDS = ("osy_id",) + FIELDS + ("photo", "archived_at")
LIMITS = {"full_name": 150, "address": 500, "contact_number": 30, "last_school": 180, "reason_stopped": 1000}


def age(birthdate):
    born = date.fromisoformat(birthdate)
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def validate(values):
    result = {key: str(values.get(key) or "").strip() for key in FIELDS}
    errors = []
    for key in ("full_name", "address"):
        if not result[key]:
            errors.append(f"{LABELS[key]} is required.")
    for key, limit in LIMITS.items():
        if len(result[key]) > limit:
            errors.append(f"{LABELS[key]} must be at most {limit} characters.")
    for key in ("birthdate", "date_registered"):
        try:
            parsed = date.fromisoformat(result[key])
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", result[key]) or not date(1900, 1, 1) <= parsed <= date.today():
                raise ValueError()
        except ValueError:
            errors.append(f"{LABELS[key]} must be YYYY-MM-DD, between 1900 and today.")
    if not errors and result["date_registered"] < result["birthdate"]:
        errors.append("Registration date cannot be before birthdate.")
    for key, options in CHOICES.items():
        if result[key] not in options:
            errors.append(f"Choose a valid {LABELS[key].lower()}.")
    if result["contact_number"] and not re.fullmatch(r"[0-9+()\s-]{7,30}", result["contact_number"]):
        errors.append("Enter a valid contact number, or leave it blank.")
    if errors:
        raise ValueError("\n".join(errors))
    return result


class Store:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.photos = self.folder / "photos"
        self.photos.mkdir(parents=True, exist_ok=True)
        # The legacy PHP app may still live under Apache's document root.
        protection = self.folder / ".htaccess"
        if not protection.exists():
            protection.write_text("Require all denied\n", encoding="ascii")
        self.path = self.folder / "osy.sqlite3"
        self.db = sqlite3.connect(self.path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                failures INTEGER NOT NULL DEFAULT 0, blocked_until REAL NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS id_sequences (year INTEGER PRIMARY KEY, next_number INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS osy_records (
                id INTEGER PRIMARY KEY, osy_id TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL,
                birthdate TEXT NOT NULL, sex TEXT NOT NULL, address TEXT NOT NULL,
                contact_number TEXT NOT NULL DEFAULT '', educational_attainment TEXT NOT NULL,
                last_school TEXT NOT NULL DEFAULT '', reason_stopped TEXT NOT NULL DEFAULT '',
                employment_status TEXT NOT NULL, date_registered TEXT NOT NULL, status TEXT NOT NULL,
                photo TEXT, archived_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX IF NOT EXISTS idx_desktop_name ON osy_records(full_name);
        """)

    def close(self):
        self.db.close()

    def is_ready(self):
        return bool(self.db.execute("SELECT 1 FROM admins LIMIT 1").fetchone())

    def setup(self, username, password, confirmation):
        username = username.strip()
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,50}", username):
            raise ValueError("Username must have 3-50 letters, numbers, dots, underscores or hyphens.")
        if not 8 <= len(password) <= 128:
            raise ValueError("Password must have 8-128 characters.")
        if password != confirmation:
            raise ValueError("Passwords do not match.")
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.is_ready():
                raise ValueError("An administrator already exists. Please sign in.")
            self.db.execute("INSERT INTO admins(username,password_hash) VALUES (?,?)",
                            (username, f"pbkdf2_sha256$600000${salt}${digest}"))

    def login(self, username, password):
        import time
        row = self.db.execute("SELECT * FROM admins WHERE username=?", (username.strip(),)).fetchone()
        if row and row["blocked_until"] > time.time():
            raise ValueError("Too many attempts. Please wait one minute.")
        encoded = row["password_hash"] if row else "pbkdf2_sha256$600000$" + "00" * 16 + "$" + "00" * 32
        _, iterations, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        valid = hmac.compare_digest(actual, expected) and row is not None
        if row:
            failures = 0 if valid else row["failures"] + 1
            blocked = time.time() + 60 if failures >= 5 else 0
            with self.db:
                self.db.execute("UPDATE admins SET failures=?, blocked_until=? WHERE id=?",
                                (0 if blocked else failures, blocked, row["id"]))
        if not valid:
            raise ValueError("The username or password is incorrect.")
        return row["username"]

    def organization(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='organization'").fetchone()
        return row[0] if row else "Community Youth Affairs"

    def set_organization(self, name):
        name = name.strip()
        if not name or len(name) > 120:
            raise ValueError("Organization name must contain 1-120 characters.")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('organization',?)", (name,))

    def get(self, record_id):
        row = self.db.execute("SELECT * FROM osy_records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise ValueError("This record no longer exists.")
        return dict(row)

    def records(self, search="", archived=False, **filters):
        where = ["archived_at IS NOT NULL" if archived else "archived_at IS NULL"]
        params = []
        if search.strip():
            term = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            where.append("(full_name LIKE ? ESCAPE '\\' OR osy_id LIKE ? ESCAPE '\\')")
            params.extend([term, term])
        for key in ("sex", "status", "employment_status"):
            if filters.get(key) in CHOICES[key]:
                where.append(f"{key}=?")
                params.append(filters[key])
        return [dict(row) for row in self.db.execute("SELECT * FROM osy_records WHERE " + " AND ".join(where)
                                                    + " ORDER BY date_registered DESC, id DESC", params)]

    def photo_path(self, filename):
        if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
            return None
        path = self.photos / filename
        return path if path.is_file() else None

    def copy_photo(self, source):
        from PIL import Image, ImageOps
        source = Path(source)
        if source.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Photo must be 2 MB or smaller.")
        with Image.open(source) as picture:
            if picture.format not in ("JPEG", "PNG", "WEBP") or max(picture.size) > 8000:
                raise ValueError("Use a JPG, PNG or WebP photo up to 8000 pixels per side.")
            picture.load()
            picture = ImageOps.exif_transpose(picture).convert("RGB")
            picture.thumbnail((1200, 1200))
            name = secrets.token_hex(16) + ".jpg"
            picture.save(self.photos / name, quality=92)
        return name

    def save(self, values, record_id=None, photo_source=None, remove_photo=False):
        data = validate(values)
        existing = self.get(record_id) if record_id else None
        new_photo = self.copy_photo(photo_source) if photo_source else None
        data["photo"] = new_photo or (None if remove_photo else (existing or {}).get("photo"))
        try:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                if existing:
                    self.db.execute("UPDATE osy_records SET " + ",".join(f"{key}=?" for key in data)
                                    + ",updated_at=CURRENT_TIMESTAMP WHERE id=?", (*data.values(), record_id))
                else:
                    year = date.today().year
                    self.db.execute("INSERT OR IGNORE INTO id_sequences VALUES (?,1)", (year,))
                    number = self.db.execute("SELECT next_number FROM id_sequences WHERE year=?", (year,)).fetchone()[0]
                    data["osy_id"] = f"OSY-{year}-{number:04d}"
                    self.db.execute("UPDATE id_sequences SET next_number=next_number+1 WHERE year=?", (year,))
                    cursor = self.db.execute("INSERT INTO osy_records (" + ",".join(data) + ") VALUES ("
                                             + ",".join("?" for _ in data) + ")", tuple(data.values()))
                    record_id = cursor.lastrowid
        except Exception:
            if new_photo:
                (self.photos / new_photo).unlink(missing_ok=True)
            raise
        return record_id

    def archive(self, record_id, archived=True):
        self.get(record_id)
        with self.db:
            self.db.execute("UPDATE osy_records SET archived_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                            (datetime.now().isoformat(timespec="seconds") if archived else None, record_id))

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path.resolve() or self.photos.resolve() in destination.parents:
            raise ValueError("Save the backup outside the database and photos folder.")
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "osy.sqlite3"
            with closing(sqlite3.connect(snapshot)) as target:
                self.db.backup(target)
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "osy.sqlite3")
                for row in self.db.execute("SELECT DISTINCT photo FROM osy_records WHERE photo IS NOT NULL"):
                    path = self.photo_path(row[0])
                    if path:
                        archive.write(path, "photos/" + path.name)

    def import_csv(self, source, photos_folder=None):
        """Import header-based records CSV atomically; never execute SQL from a dump."""
        with open(source, newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            missing = set(("osy_id",) + FIELDS) - set(reader.fieldnames or ())
            if missing:
                raise ValueError("CSV needs column headers. Missing: " + ", ".join(sorted(missing)))
            rows = list(reader)
        copied = []
        missing_photos = 0
        try:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                for line, row in enumerate(rows, 2):
                    try:
                        data = validate(row)
                        match = re.fullmatch(r"OSY-(\d{4})-(\d{4,})", row["osy_id"] or "")
                        if not match:
                            raise ValueError("Invalid OSY ID.")
                        year, number = map(int, match.groups())
                        data["osy_id"] = row["osy_id"]
                        archived = row.get("archived_at")
                        if archived in (None, "", "NULL", "\\N"):
                            archived = None
                        elif archived:
                            datetime.fromisoformat(archived)
                        data["archived_at"] = archived
                        data["photo"] = None
                        photo = row.get("photo")
                        if photo and photo not in ("NULL", "\\N"):
                            if Path(photo).name != photo or "/" in photo or "\\" in photo:
                                raise ValueError("Photo must be a filename only.")
                            path = Path(photos_folder) / photo if photos_folder else None
                            if path and path.is_file():
                                data["photo"] = self.copy_photo(path)
                                copied.append(data["photo"])
                            else:
                                missing_photos += 1
                        self.db.execute("INSERT INTO osy_records (" + ",".join(data) + ") VALUES ("
                                        + ",".join("?" for _ in data) + ")", tuple(data.values()))
                        self.db.execute("INSERT INTO id_sequences VALUES (?,?) ON CONFLICT(year) DO UPDATE SET "
                                        "next_number=MAX(next_number,excluded.next_number)", (year, number + 1))
                    except (ValueError, sqlite3.IntegrityError) as error:
                        raise ValueError(f"CSV row {line}: {error}\nNo records were imported.") from error
        except Exception:
            for name in copied:
                (self.photos / name).unlink(missing_ok=True)
            raise
        return len(rows), missing_photos


def export_csv(rows, destination):
    with open(destination, "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
