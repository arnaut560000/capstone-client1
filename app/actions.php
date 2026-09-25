<?php
function saveRecord(?array $existing): array {
    $data = []; $errors = [];
    $limits = ['full_name' => 150, 'address' => 250, 'contact_number' => 30, 'educational_attainment' => 80, 'last_school' => 180, 'reason_stopped' => 1000];
    foreach (array_merge(array_keys($limits), ['birthdate', 'sex', 'employment_status', 'date_registered', 'status']) as $key) $data[$key] = trim((string)($_POST[$key] ?? ''));
    foreach (['full_name' => 'Full name', 'address' => 'Address'] as $key => $label) if ($data[$key] === '') $errors[] = "$label is required.";
    foreach ($limits as $key => $limit) if (mb_strlen($data[$key]) > $limit) $errors[] = ucfirst(str_replace('_', ' ', $key)) . " must be at most $limit characters.";
    if (!validDate($data['birthdate']) || $data['birthdate'] > date('Y-m-d') || $data['birthdate'] < '1900-01-01') $errors[] = 'Enter a valid birthdate between 1900 and today.';
    if (!validDate($data['date_registered']) || $data['date_registered'] > date('Y-m-d') || $data['date_registered'] < '1900-01-01') $errors[] = 'Enter a valid registration date that is not in the future.';
    if (validDate($data['birthdate']) && validDate($data['date_registered']) && $data['date_registered'] < $data['birthdate']) $errors[] = 'Registration date cannot be before the birthdate.';
    foreach (['sex' => ['Male', 'Female'], 'educational_attainment' => EDUCATION, 'employment_status' => ['Employed', 'Unemployed'], 'status' => ['Active', 'Inactive']] as $key => $allowed) if (!in_array($data[$key], $allowed, true)) $errors[] = 'Choose a valid ' . str_replace('_', ' ', $key) . '.';
    if ($data['contact_number'] !== '' && !preg_match('/^[0-9+()\s-]{7,30}$/', $data['contact_number'])) $errors[] = 'Enter a valid contact number, or leave it blank.';
    $photo = $_FILES['photo'] ?? null; $extension = null;
    if ($photo && $photo['error'] !== UPLOAD_ERR_NO_FILE) {
        if ($photo['error'] !== UPLOAD_ERR_OK) $errors[] = 'The photo could not be uploaded. Please use an image smaller than 2 MB.';
        elseif ($photo['size'] > 2 * 1024 * 1024) $errors[] = 'Profile photo must be 2 MB or smaller.';
        else {
            $mime = (new finfo(FILEINFO_MIME_TYPE))->file($photo['tmp_name']);
            $extension = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'][$mime] ?? null;
            $dimensions = @getimagesize($photo['tmp_name']);
            if (!$extension || !$dimensions || $dimensions[0] > 8000 || $dimensions[1] > 8000) $errors[] = 'Use a valid JPG, PNG or WebP photo up to 8000 pixels per side.';
        }
    }
    if ($errors) return [$data, $errors];
    $newPhoto = null;
    if ($extension) {
        $dir = __DIR__ . '/../storage/photos';
        if (!is_dir($dir) && !mkdir($dir, 0755, true)) throw new RuntimeException('Cannot create photo storage.');
        $newPhoto = bin2hex(random_bytes(16)) . '.' . $extension;
        if (!move_uploaded_file($photo['tmp_name'], $dir . '/' . $newPhoto)) throw new RuntimeException('Cannot save photo. Check storage folder permissions.');
    }
    $data['photo'] = $newPhoto ?: ($existing['photo'] ?? null);
    $pdo = db();
    try {
        $pdo->beginTransaction();
        if ($existing) {
            $assignments = implode(', ', array_map(fn($key) => "$key = ?", array_keys($data)));
            $pdo->prepare("UPDATE osy_records SET $assignments WHERE id = ?")->execute([...array_values($data), $existing['id']]); $id = $existing['id'];
        } else {
            $year = (int)date('Y');
            $pdo->prepare('INSERT IGNORE INTO id_sequences (year, next_number) VALUES (?, 1)')->execute([$year]);
            $stmt = $pdo->prepare('SELECT next_number FROM id_sequences WHERE year = ? FOR UPDATE'); $stmt->execute([$year]); $number = (int)$stmt->fetchColumn();
            $pdo->prepare('UPDATE id_sequences SET next_number = next_number + 1 WHERE year = ?')->execute([$year]);
            $data['osy_id'] = sprintf('OSY-%d-%04d', $year, $number);
            $pdo->prepare('INSERT INTO osy_records (' . implode(',', array_keys($data)) . ') VALUES (' . implode(',', array_fill(0, count($data), '?')) . ')')->execute(array_values($data)); $id = $pdo->lastInsertId();
        }
        $pdo->commit();
    } catch (Throwable $error) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        if ($newPhoto) @unlink(__DIR__ . '/../storage/photos/' . $newPhoto);
        throw $error;
    }
    if ($newPhoto && !empty($existing['photo'])) @unlink(__DIR__ . '/../storage/photos/' . basename($existing['photo']));
    flash($existing ? 'OSY record updated successfully.' : 'Registration complete. Your OSY ID card is ready to preview.');
    redirect('profile', ['id' => $id]);
}
