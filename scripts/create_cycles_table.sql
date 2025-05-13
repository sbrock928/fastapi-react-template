-- Create cycles table 
CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert test cycle codes
INSERT OR IGNORE INTO cycles (code, description, start_date, end_date) 
VALUES 
    ('12501', 'January 2023 Cycle', '2023-01-01', '2023-01-31'),
    ('12502', 'February 2023 Cycle', '2023-02-01', '2023-02-28'),
    ('12503', 'March 2023 Cycle', '2023-03-01', '2023-03-31'),
    ('12504', 'April 2023 Cycle', '2023-04-01', '2023-04-30');
