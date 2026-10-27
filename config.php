<?php
// Browser application storage. No MySQL service or database credentials needed.
return [
    'storage' => getenv('OSY_WEB_STORAGE') ?: __DIR__ . '/storage',
    'organization' => 'Community Youth Affairs',
];
