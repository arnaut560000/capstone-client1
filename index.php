<?php
require __DIR__ . '/app/bootstrap.php';
require __DIR__ . '/app/actions.php';
$page = (string)($_GET['page'] ?? 'dashboard');
$views = ['dashboard' => 'dashboard', 'records' => 'records', 'idcards' => 'records', 'reports' => 'records', 'register' => 'form', 'edit' => 'form', 'profile' => 'profile', 'card' => 'card', 'login' => 'auth', 'setup' => 'auth'];
$error = null; $errors = []; $ready = false;
try { $ready = (bool)db()->query('SELECT COUNT(*) FROM admins')->fetchColumn(); } catch (PDOException $exception) { /* Setup screen explains local configuration. */ }
if (!$ready && $page !== 'setup') redirect('setup');
if ($ready && $page === 'setup') redirect(isset($_SESSION['admin_id']) ? 'dashboard' : 'login');
if (!in_array($page, ['login', 'setup'], true) && !isset($_SESSION['admin_id'])) redirect('login');
if ($_SERVER['REQUEST_METHOD'] === 'POST') checkCsrf();
try {
    if ($page === 'setup' && $_SERVER['REQUEST_METHOD'] === 'POST') {
        $username = trim((string)($_POST['username'] ?? '')); $password = (string)($_POST['password'] ?? '');
        if (!preg_match('/^[a-zA-Z0-9_.-]{3,50}$/', $username)) $errors[] = 'Use a username of 3–50 letters, numbers, dots, underscores or hyphens.';
        if (strlen($password) < 8 || strlen($password) > 72) $errors[] = 'Use a password between 8 and 72 characters.';
        if ($password !== ($_POST['confirm_password'] ?? '')) $errors[] = 'The passwords do not match.';
        if (!$errors) {
            $server = db(false); $server->exec('CREATE DATABASE IF NOT EXISTS `' . $config['database'] . '` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');
            db()->exec(file_get_contents(__DIR__ . '/database.sql'));
            if (!(int)db()->query("SELECT GET_LOCK('osy_first_admin_setup', 10)")->fetchColumn()) throw new RuntimeException('Setup is busy. Please try again.');
            try {
                if ((int)db()->query('SELECT COUNT(*) FROM admins')->fetchColumn() !== 0) throw new RuntimeException('Setup is already complete. Please sign in.');
                db()->prepare('INSERT INTO admins (username, password_hash) VALUES (?, ?)')->execute([$username, password_hash($password, PASSWORD_DEFAULT)]);
            } finally { db()->query("SELECT RELEASE_LOCK('osy_first_admin_setup')"); }
            flash('Setup complete. Sign in with your new admin account.'); redirect('login');
        }
    }
    if ($page === 'login' && $_SERVER['REQUEST_METHOD'] === 'POST') {
        if (($_SESSION['login_blocked_until'] ?? 0) > time()) $errors[] = 'Too many attempts. Please wait one minute and try again.';
        else {
            $stmt = db()->prepare('SELECT * FROM admins WHERE username = ?'); $stmt->execute([trim((string)($_POST['username'] ?? ''))]); $admin = $stmt->fetch();
            if ($admin && password_verify((string)($_POST['password'] ?? ''), $admin['password_hash'])) {
                session_regenerate_id(true); $_SESSION['admin_id'] = $admin['id']; $_SESSION['username'] = $admin['username']; unset($_SESSION['login_attempts'], $_SESSION['login_blocked_until']); redirect('dashboard');
            }
            $_SESSION['login_attempts'] = ($_SESSION['login_attempts'] ?? 0) + 1;
            if ($_SESSION['login_attempts'] >= 5) { $_SESSION['login_blocked_until'] = time() + 60; $_SESSION['login_attempts'] = 0; }
            $errors[] = 'The username or password is incorrect.';
        }
    }
    if ($page === 'logout' && $_SERVER['REQUEST_METHOD'] === 'POST') { $_SESSION = []; session_destroy(); redirect('login'); }
    if (in_array($page, ['edit', 'profile', 'card', 'photo', 'archive', 'restore'], true)) $person = record((int)($_GET['id'] ?? 0));
    if ($page === 'photo') {
        $file = __DIR__ . '/storage/photos/' . basename($person['photo'] ?? '');
        if (empty($person['photo']) || !is_file($file)) { http_response_code(404); exit; }
        header('Content-Type: ' . (new finfo(FILEINFO_MIME_TYPE))->file($file)); readfile($file); exit;
    }
    if (in_array($page, ['archive', 'restore'], true) && $_SERVER['REQUEST_METHOD'] === 'POST') {
        db()->prepare('UPDATE osy_records SET archived_at = ' . ($page === 'archive' ? 'NOW()' : 'NULL') . ' WHERE id = ?')->execute([$person['id']]);
        flash($page === 'archive' ? 'Record archived. You can restore it from Archived records.' : 'Record restored successfully.'); redirect('records', $page === 'archive' ? [] : ['archived' => 1]);
    }
    if (in_array($page, ['register', 'edit'], true)) {
        $data = $person ?? ['full_name' => '', 'birthdate' => '', 'sex' => '', 'address' => '', 'contact_number' => '', 'educational_attainment' => '', 'last_school' => '', 'reason_stopped' => '', 'employment_status' => 'Unemployed', 'date_registered' => date('Y-m-d'), 'status' => 'Active'];
        if ($_SERVER['REQUEST_METHOD'] === 'POST') [$data, $errors] = saveRecord($person ?? null);
    }
    if (!isset($views[$page])) { http_response_code(404); $error = 'Page not found.'; }
} catch (Throwable $exception) {
    error_log((string)$exception);
    if ($exception instanceof PDOException) $errors[] = 'Could not connect to or update the database. Start MySQL in XAMPP and check config.php.';
    else $errors[] = $exception->getMessage();
    if (!in_array($page, ['login', 'setup', 'register', 'edit'], true)) $error = end($errors);
}
$titles = ['dashboard' => 'Dashboard', 'records' => 'OSY records', 'register' => 'Register OSY', 'edit' => 'Edit OSY record', 'profile' => 'OSY profile', 'idcards' => 'ID generation', 'card' => 'ID preview', 'reports' => 'Reports', 'login' => 'Welcome back', 'setup' => 'Let’s get you set up'];
$title = $titles[$page] ?? 'Page not found';
require __DIR__ . '/app/layout.php';
