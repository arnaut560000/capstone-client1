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
        $dir = webStoragePath('photos');
        if (!is_dir($dir) && !mkdir($dir, 0755, true)) throw new RuntimeException('Cannot create photo storage.');
        $newPhoto = bin2hex(random_bytes(16)) . '.' . $extension;
        if (!move_uploaded_file($photo['tmp_name'], $dir . '/' . $newPhoto)) throw new RuntimeException('Cannot save photo. Check storage folder permissions.');
    }
    $data['photo'] = $newPhoto ?: ($existing['photo'] ?? null);
    try {
        $id = writeTransaction(db(), function (PDO $pdo) use ($existing, $data): int {
        if ($existing) {
            $assignments = implode(', ', array_map(fn($key) => "$key = ?", array_keys($data)));
            $pdo->prepare("UPDATE osy_records SET $assignments, updated_at = CURRENT_TIMESTAMP WHERE id = ?")->execute([...array_values($data), $existing['id']]); $id = $existing['id'];
        } else {
            $data['osy_id'] = allocateOsyId($pdo);
            $pdo->prepare('INSERT INTO osy_records (' . implode(',', array_keys($data)) . ') VALUES (' . implode(',', array_fill(0, count($data), '?')) . ')')->execute(array_values($data)); $id = $pdo->lastInsertId();
        }
        return (int)$id;
        });
    } catch (Throwable $error) {
        if ($newPhoto) @unlink(webStoragePath('photos/' . $newPhoto));
        throw $error;
    }
    if ($newPhoto && !empty($existing['photo'])) @unlink(webStoragePath('photos/' . basename($existing['photo'])));
    flash($existing ? 'OSY record updated successfully.' : 'Registration complete. Your OSY ID card is ready to preview.');
    redirect('profile', ['id' => $id]);
}
