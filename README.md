# OSY Connect

A simple Out-of-School Youth Monitoring System with ID Generation. Built with PHP 8.1+ and MySQL / MariaDB for XAMPP. No framework, Composer, npm, or internet connection is needed.

## Run with XAMPP

1. Copy this entire `capstone` folder into `C:\xampp\htdocs\`.
2. Open the XAMPP Control Panel and start **Apache** and **MySQL**.
3. Visit **http://localhost/capstone/** in your browser.
4. The setup screen creates the `osy_monitoring` database and its tables. Choose your admin username and password (at least 8 characters), then sign in.

The database defaults are `127.0.0.1`, port `3306`, username `root`, and an empty password. Change `config.php` if your XAMPP settings differ. Setup requires a database account with permission to create databases and tables. Alternatively, create the database in phpMyAdmin and import `database.sql`, then visit the app to create the admin account.

The setup page is disabled after the first administrator is created. There are no shared default login credentials. This project is intended for a local capstone demonstration.

## Features

- **Admin login:** password hashing, login, and logout.
- **Registration:** personal details, optional photo, education, employment, and registration status. Age is calculated from birthdate.
- **Automatic OSY IDs:** `OSY-2026-0001`, using the current registration year and a database transaction. The counter starts at 0001 each calendar year; existing IDs stay unchanged when editing.
- **Records:** search by name or OSY ID, filter, view, edit, archive, and restore. Archiving is the reversible alternative to permanent deletion.
- **Profiles:** complete personal, educational, employment, and registration details.
- **ID generation:** automatic printable card based on each saved record, with photo or initials. Select **Preview ID → Print ID**.
- **Dashboard:** registered total, male, female, active, employment totals, age groups, and recent registrations. Archived records are excluded; inactive records remain included in the registered total.
- **Reports:** filter the master list by name/ID, sex, record status, and employment. Print the filtered list or use the browser’s **Save as PDF** option. All matching records are included.

## Typical workflow

Sign in → Register OSY → Save registration → Preview ID → Print ID. Use OSY records to edit or archive profiles, and Reports to print the master list.

Use the logout icon beside the administrator name at the bottom of the sidebar. On narrow mobile screens, use the **Log out** link in the top bar.

For IDs, use **100% / actual size**, turn off browser headers and footers, and enable background graphics. The card is 86 × 54 mm. Check the preview for unusually long names or addresses before printing. Reports use A4 landscape.

## Files

- `index.php`: request routing and authentication.
- `config.php`: database connection and organization name printed on reports/IDs.
- `database.sql`: the three database tables.
- `app/`: helpers, record saving, templates.
- `assets/`: local stylesheet and small JavaScript helpers.
- `storage/photos/`: uploaded profile pictures, served only after signing in.
- `router.php`: protected router for the optional PHP development server.

Photo uploads accept JPG, PNG, and WebP up to 2 MB. PHP must have PDO MySQL, fileinfo, and mbstring enabled (included in typical XAMPP installations). Ensure PHP's `upload_max_filesize` is at least `2M`, `post_max_size` is larger (e.g. `8M`), and `storage/photos` is writable.

Sessions are stored in `storage/sessions/`, which PHP creates automatically. The entire `storage` folder must be writable. Apache blocks direct access to storage, application helpers, and configuration through the included `.htaccess` files.

## Optional development server

Keep XAMPP MySQL running, open PowerShell in this folder, and run:

```powershell
C:\xampp\php\php.exe -S 127.0.0.1:8080 router.php
```

Open **http://127.0.0.1:8080/**. Use the provided router so configuration and uploaded files cannot be downloaded directly.

## Backups

Export `osy_monitoring` from phpMyAdmin and copy `storage/photos/` together. Both are needed to restore records and photos. Use invented data for demonstrations. There is no seed data added to your real database.

## Development verification

The project was checked with PHP 8.2 and MariaDB 10.4. `tests/integration.py` exercises setup, authentication, validation, photo uploads, sequential IDs, search, filtering, editing, escaping, archive/restore, protected routes, and logout (31 checks).

To repeat it, start the development server against a **new disposable database** using the `OSY_DB_NAME` environment variable (for example `osy_capstone_test`) and visit no setup page manually beforehand. The test targets `http://127.0.0.1:8080/` and stops if the fresh setup page is not available. Run `python tests/integration.py`. Its admin credentials and two fictional records are only for that disposable database; do not use them for your real installation. Database host, port, username, and password can also be overridden through `OSY_DB_HOST`, `OSY_DB_PORT`, `OSY_DB_USER`, and `OSY_DB_PASSWORD`.
