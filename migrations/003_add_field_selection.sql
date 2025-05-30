-- Add Field Selection to Reports Migration
-- Adds the report_fields table to support dynamic field selection

-- Create the report_fields table
CREATE TABLE IF NOT EXISTS report_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    field_type VARCHAR(50) NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_report_fields_report_id ON report_fields(report_id);
CREATE INDEX IF NOT EXISTS idx_report_fields_field_name ON report_fields(field_name);

-- Add field_count to existing reports by creating a view or trigger
-- (This is just for reference - the service will calculate it dynamically)