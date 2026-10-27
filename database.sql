CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS id_sequences (
    year INTEGER PRIMARY KEY,
    next_number INTEGER NOT NULL DEFAULT 1 CHECK (next_number > 0)
);

CREATE TABLE IF NOT EXISTS osy_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osy_id TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    birthdate TEXT NOT NULL,
    sex TEXT NOT NULL CHECK (sex IN ('Male', 'Female')),
    address TEXT NOT NULL,
    contact_number TEXT NOT NULL DEFAULT '',
    educational_attainment TEXT NOT NULL,
    last_school TEXT NOT NULL DEFAULT '',
    reason_stopped TEXT NOT NULL DEFAULT '',
    employment_status TEXT NOT NULL CHECK (employment_status IN ('Employed', 'Unemployed')),
    date_registered TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive')),
    photo TEXT DEFAULT NULL,
    archived_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_name ON osy_records(full_name);
CREATE INDEX IF NOT EXISTS idx_archived ON osy_records(archived_at);
