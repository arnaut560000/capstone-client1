CREATE TABLE IF NOT EXISTS admins (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS id_sequences (
    year SMALLINT UNSIGNED PRIMARY KEY,
    next_number INT UNSIGNED NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS osy_records (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    osy_id VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    birthdate DATE NOT NULL,
    sex ENUM('Male','Female') NOT NULL,
    address VARCHAR(500) NOT NULL,
    contact_number VARCHAR(30) NOT NULL DEFAULT '',
    educational_attainment VARCHAR(80) NOT NULL,
    last_school VARCHAR(180) NOT NULL DEFAULT '',
    reason_stopped VARCHAR(1000) NOT NULL DEFAULT '',
    employment_status ENUM('Employed','Unemployed') NOT NULL,
    date_registered DATE NOT NULL,
    status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
    photo VARCHAR(80) DEFAULT NULL,
    archived_at DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (full_name),
    INDEX idx_archived (archived_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
