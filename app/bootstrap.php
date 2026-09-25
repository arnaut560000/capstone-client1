<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Manila');
$sessionDirectory = __DIR__ . '/../storage/sessions';
if (!is_dir($sessionDirectory)) mkdir($sessionDirectory, 0700, true);
session_save_path($sessionDirectory);
session_name('OSY_CONNECT_SESSION');
ini_set('session.use_strict_mode', '1');
session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax', 'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off']);
session_start();
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: SAMEORIGIN');
header('Cache-Control: no-store');
$config = require __DIR__ . '/../config.php';
const EDUCATION = ['No formal education', 'Elementary level', 'Elementary graduate', 'Junior high school level', 'Junior high school graduate', 'Senior high school level', 'Senior high school graduate', 'Vocational / Technical', 'College level', 'College graduate'];

function db(bool $withDatabase = true): PDO {
    global $config;
    static $connection;
    if ($withDatabase && $connection) return $connection;
    if (!preg_match('/^[a-zA-Z0-9_]+$/', $config['database'])) throw new RuntimeException('Invalid database name.');
    $dsn = 'mysql:host=' . $config['host'] . ';port=' . $config['port'] . ($withDatabase ? ';dbname=' . $config['database'] : '') . ';charset=utf8mb4';
    $pdo = new PDO($dsn, $config['username'], $config['password'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, PDO::ATTR_EMULATE_PREPARES => false]);
    if ($withDatabase) $connection = $pdo;
    return $pdo;
}
function e(mixed $value): string { return htmlspecialchars((string)($value ?? ''), ENT_QUOTES, 'UTF-8'); }
function url(string $page, array $params = []): string { return 'index.php?' . http_build_query(['page' => $page] + $params); }
function redirect(string $page, array $params = []): never { header('Location: ' . url($page, $params)); exit; }
function csrf(): string { $_SESSION['csrf'] ??= bin2hex(random_bytes(32)); return '<input type="hidden" name="csrf" value="' . e($_SESSION['csrf']) . '">'; }
function checkCsrf(): void {
    if (empty($_SESSION['csrf']) || !is_string($_POST['csrf'] ?? null) || !hash_equals($_SESSION['csrf'], $_POST['csrf'])) { http_response_code(403); exit('Your session expired. Go back, refresh the page, and try again.'); }
}
function flash(string $message): void { $_SESSION['flash'] = $message; }
function age(string $birthdate): int { return (new DateTimeImmutable($birthdate))->diff(new DateTimeImmutable('today'))->y; }
function formattedDate(string $date): string { return (new DateTimeImmutable($date))->format('F j, Y'); }
function initials(string $name): string { $words = preg_split('/\s+/', trim($name)); return strtoupper(substr($words[0] ?? '', 0, 1) . (count($words) > 1 ? substr(end($words), 0, 1) : '')); }
function avatar(array $record, string $class = ''): string {
    return !empty($record['photo']) ? '<img class="avatar ' . e($class) . '" src="' . e(url('photo', ['id' => $record['id']])) . '" alt="Photo of ' . e($record['full_name']) . '">' : '<span class="avatar ' . e($class) . '">' . e(initials($record['full_name'])) . '</span>';
}
function badge(string $status): string { return '<span class="badge ' . strtolower(e($status)) . '"><span></span>' . e($status) . '</span>'; }
function record(int $id): array {
    $stmt = db()->prepare('SELECT * FROM osy_records WHERE id = ?'); $stmt->execute([$id]);
    $row = $stmt->fetch(); if (!$row) { http_response_code(404); throw new RuntimeException('This OSY record was not found.'); } return $row;
}
function validDate(string $value): bool { $d = DateTimeImmutable::createFromFormat('!Y-m-d', $value); return $d && $d->format('Y-m-d') === $value; }
function filteredRecords(bool $archived = false): array {
    $where = ['archived_at IS ' . ($archived ? 'NOT NULL' : 'NULL')]; $params = [];
    $search = trim((string)($_GET['q'] ?? ''));
    if ($search !== '') { $where[] = '(full_name LIKE ? OR osy_id LIKE ?)'; $params[] = '%' . $search . '%'; $params[] = '%' . $search . '%'; }
    foreach (['sex' => ['Male', 'Female'], 'status' => ['Active', 'Inactive'], 'employment_status' => ['Employed', 'Unemployed']] as $key => $allowed) {
        if (in_array($_GET[$key] ?? '', $allowed, true)) { $where[] = "$key = ?"; $params[] = $_GET[$key]; }
    }
    $stmt = db()->prepare('SELECT * FROM osy_records WHERE ' . implode(' AND ', $where) . ' ORDER BY date_registered DESC, id DESC'); $stmt->execute($params); return $stmt->fetchAll();
}
function icon(string $name): string {
    $paths = [
        'dashboard' => '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
        'records' => '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
        'register' => '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2m4-13v6m-3-3h6"/>',
        'idcards' => '<rect x="2" y="4" width="20" height="16" rx="3"/><circle cx="8" cy="10" r="2"/><path d="M5 16c0-3 6-3 6 0m4-7h4m-4 4h4"/>',
        'reports' => '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zm0 0v6h6M8 13h8m-8 4h5"/>',
        'logout' => '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4m7 14 5-5-5-5m5 5H9"/>',
        'search' => '<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
        'arrow' => '<path d="M5 12h14m-5-5 5 5-5 5"/>',
        'print' => '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/>',
    ];
    return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' . ($paths[$name] ?? $paths['records']) . '</svg>';
}
