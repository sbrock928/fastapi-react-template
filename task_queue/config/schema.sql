-- SQL script for creating report scheduling and execution tables

-- Table for storing scheduled reports
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parameters JSONB NOT NULL,
    frequency VARCHAR(50) NOT NULL, -- 'DAILY', 'WEEKLY', 'MONTHLY'
    day_of_week VARCHAR(10), -- For weekly reports: 'MONDAY', 'TUESDAY', etc.
    day_of_month INTEGER, -- For monthly reports: 1-31
    time_of_day TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_report FOREIGN KEY (report_id) REFERENCES reports(id),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT valid_frequency CHECK (frequency IN ('DAILY', 'WEEKLY', 'MONTHLY')),
    CONSTRAINT valid_day_of_week CHECK (
        (frequency != 'WEEKLY') OR 
        (day_of_week IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'))
    ),
    CONSTRAINT valid_day_of_month CHECK (
        (frequency != 'MONTHLY') OR
        (day_of_month BETWEEN 1 AND 31)
    )
);

-- Table for tracking report executions
CREATE TABLE IF NOT EXISTS report_executions (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL,
    scheduled_report_id INTEGER,
    task_id VARCHAR(255),
    user_id INTEGER,
    status VARCHAR(50) NOT NULL, -- 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'
    parameters JSONB NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result_path VARCHAR(255),
    error TEXT,
    CONSTRAINT fk_report FOREIGN KEY (report_id) REFERENCES reports(id),
    CONSTRAINT fk_scheduled_report FOREIGN KEY (scheduled_report_id) REFERENCES scheduled_reports(id),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT valid_status CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'))
);

-- Table for user notifications
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'REPORT_COMPLETION', 'SYSTEM', etc.
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reference_id INTEGER,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_user_id ON scheduled_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_report_id ON scheduled_reports(report_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_frequency ON scheduled_reports(frequency);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_is_active ON scheduled_reports(is_active);

CREATE INDEX IF NOT EXISTS idx_report_executions_report_id ON report_executions(report_id);
CREATE INDEX IF NOT EXISTS idx_report_executions_task_id ON report_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_report_executions_user_id ON report_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_report_executions_status ON report_executions(status);
CREATE INDEX IF NOT EXISTS idx_report_executions_started_at ON report_executions(started_at);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
