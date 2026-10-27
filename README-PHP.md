# OSY Connect - PHP browser version with SQLite

The browser interface now uses PHP 8.1+ and SQLite. MySQL and phpMyAdmin are not needed. The existing design, registration, dashboard, profiles, ID cards, and reports are retained.

## Run without XAMPP services

Install or supply a PHP runtime with `pdo_sqlite`, `fileinfo`, and `mbstring` enabled. In this project folder, run:

```powershell
php -S 127.0.0.1:8080 router.php
```

Open **http://localhost:8080/**. Keep the terminal open while using the app. Use the included router so configuration, database files, and uploaded photos cannot be downloaded directly.

The app automatically creates **`storage/database/osy.sqlite3`** and its tables. Choose your own administrator username and password (8-72 characters), then sign in. The setup page is disabled after the first account is created. There is no default account and no sample data.

On this development laptop, PHP is available at `C:\xampp\php\php.exe`. Running that executable does not require starting XAMPP's Apache or MySQL services. Another laptop still needs a PHP runtime with the extensions above; a portable PHP runtime has not been bundled.

## Use the existing localhost/folder-name address

Place the project in `C:\xampp\htdocs\folder-name` and start **Apache only**. Open **http://localhost/folder-name/**. MySQL may remain stopped. Ensure Apache's PHP configuration also has `pdo_sqlite` enabled.

## Storage and existing records

- `storage/database/osy.sqlite3`: browser records, administrator account, and ID counters.
- `storage/photos/`: uploaded profile photos.
- `storage/sessions/`: temporary login sessions.
- `database.sql`: SQLite schema, applied automatically to a new database. Do not import it into MySQL.
- `config.php`: browser storage location and organization name on reports and IDs.
- `app/database.php`: SQLite connections, schema initialization, and transactions.

The storage folder must be writable. `OSY_WEB_STORAGE` can override it with an absolute local directory containing `database`, `photos`, and `sessions`. The old `OSY_DB_HOST`, `OSY_DB_NAME`, username and password settings are no longer used.

**Existing MySQL records are not automatically migrated.** The old MySQL database is not changed. Back it up before a separate migration; a new browser SQLite installation starts empty.

The browser database is separate from the Tkinter app's `desktop-data/osy.sqlite3`. Their accounts and records do not synchronize, and their database files must not be substituted for each other.
