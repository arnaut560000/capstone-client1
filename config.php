<?php
// XAMPP defaults. Change these if your MySQL settings are different.
return [
    'host' => getenv('OSY_DB_HOST') ?: '127.0.0.1',
    'port' => getenv('OSY_DB_PORT') ?: '3306',
    'database' => getenv('OSY_DB_NAME') ?: 'osy_monitoring',
    'username' => getenv('OSY_DB_USER') ?: 'root',
    'password' => getenv('OSY_DB_PASSWORD') ?: '',
    'organization' => 'Community Youth Affairs',
];
