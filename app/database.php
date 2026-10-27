<?php
declare(strict_types=1);

function webConfig(): array {
    static $config;
    return $config ??= require __DIR__ . '/../config.php';
}

function webStoragePath(string $relative = ''): string {
    return rtrim(webConfig()['storage'], '/\\') . ($relative !== '' ? '/' . $relative : '');
}

function ensureWebStorage(): void {
    $root = webStoragePath();
    if (!is_dir($root) && !@mkdir($root, 0700, true) && !is_dir($root)) {
        throw new RuntimeException('Cannot create browser storage. Check folder permissions in config.php.');
    }
    if (!is_file($root . '/.htaccess') && file_put_contents($root . '/.htaccess', "Require all denied\n") === false) {
        throw new RuntimeException('Cannot protect the browser storage folder. Check folder permissions.');
    }
}

function db(): PDO {
    static $connection;
    if ($connection instanceof PDO) return $connection;
    if (!in_array('sqlite', PDO::getAvailableDrivers(), true)) {
        throw new RuntimeException('Enable the pdo_sqlite extension in your PHP configuration. MySQL is not required.');
    }
    ensureWebStorage();
    $directory = webStoragePath('database');
    if (!is_dir($directory) && !@mkdir($directory, 0700, true) && !is_dir($directory)) {
        throw new RuntimeException('Cannot create the SQLite database folder. Check storage permissions.');
    }
    $pdo = new PDO('sqlite:' . $directory . '/osy.sqlite3', null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_TIMEOUT => 15,
    ]);
    $pdo->exec('PRAGMA foreign_keys = ON');
    $pdo->exec('PRAGMA busy_timeout = 15000');
    $version = (int)$pdo->query('PRAGMA user_version')->fetchColumn();
    if ($version > 1) throw new RuntimeException('This database needs a newer version of OSY Connect.');
    if ($version === 0) {
        writeTransaction($pdo, function (PDO $database): void {
            $schema = file_get_contents(__DIR__ . '/../database.sql');
            if ($schema === false) throw new RuntimeException('SQLite schema file is missing.');
            $database->exec($schema);
            $database->exec('PRAGMA user_version = 1');
        });
    }
    $connection = $pdo;
    return $connection;
}

function writeTransaction(PDO $pdo, callable $operation): mixed {
    // Acquire the write lock before reading counters or first-account state.
    // Use SQL COMMIT/ROLLBACK too: PDO does not track manual BEGIN consistently.
    $pdo->exec('BEGIN IMMEDIATE');
    try {
        $result = $operation($pdo);
        $pdo->exec('COMMIT');
        return $result;
    } catch (Throwable $error) {
        try { $pdo->exec('ROLLBACK'); } catch (Throwable $ignored) { /* Preserve the original error. */ }
        throw $error;
    }
}

function createAdministrator(string $username, string $password): void {
    $hash = password_hash($password, PASSWORD_DEFAULT);
    writeTransaction(db(), function (PDO $pdo) use ($username, $hash): void {
        if ((int)$pdo->query('SELECT COUNT(*) FROM admins')->fetchColumn() !== 0) {
            throw new RuntimeException('Setup is already complete. Please sign in.');
        }
        $pdo->prepare('INSERT INTO admins (username, password_hash) VALUES (?, ?)')->execute([$username, $hash]);
    });
}

// Call inside writeTransaction so concurrent registrations cannot share a number.
function allocateOsyId(PDO $pdo): string {
    $year = (int)date('Y');
    $pdo->prepare('INSERT OR IGNORE INTO id_sequences (year, next_number) VALUES (?, 1)')->execute([$year]);
    $statement = $pdo->prepare('SELECT next_number FROM id_sequences WHERE year = ?');
    $statement->execute([$year]);
    $number = (int)$statement->fetchColumn();
    $statement->closeCursor();
    $pdo->prepare('UPDATE id_sequences SET next_number = next_number + 1 WHERE year = ?')->execute([$year]);
    return sprintf('OSY-%d-%04d', $year, $number);
}
