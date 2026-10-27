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
