-- Migration: Add filter conditions support for Phase 2: Basic Filtering
-- This migration adds the filter_conditions table to support basic filtering in reports

-- Create filter_conditions table
CREATE TABLE filter_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    field_name VARCHAR NOT NULL,
    operator VARCHAR NOT NULL,
    value VARCHAR NOT NULL,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);

-- Create index for performance
CREATE INDEX idx_filter_conditions_report_id ON filter_conditions(report_id);
CREATE INDEX idx_filter_conditions_field_name ON filter_conditions(field_name);