"""
Script to create a Cycles table in the database and populate it with test data.
This quick and dirty script uses SQLAlchemy directly with your existing database.
"""
import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table

# Path to the SQLite database
DB_PATH = "sql_app.db"

# Verify the database exists
if not os.path.exists(DB_PATH):
    print(f"Error: Database file {DB_PATH} not found!")
    exit(1)

# Create SQLAlchemy engine
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)
metadata = MetaData()

# Define Cycles table
cycles_table = Table(
    "cycles",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("code", String(10), nullable=False, unique=True),
    Column("description", String(100), nullable=True),
)

# Create the table
try:
    metadata.create_all(engine)
    print("Cycles table created successfully!")
except Exception as e:
    print(f"Error creating table: {str(e)}")
    exit(1)

# Sample cycle codes to insert
cycle_codes = [
    {"code": "12403", "description": "Q1 2024 Cycle"},
    {"code": "12503", "description": "Q2 2024 Cycle"},
    {"code": "12603", "description": "Q3 2024 Cycle"},
    {"code": "12703", "description": "Q4 2024 Cycle"},
    {"code": "13403", "description": "Q1 2025 Cycle"},
    {"code": "13503", "description": "Q2 2025 Cycle"},
    {"code": "13603", "description": "Q3 2025 Cycle"},
    {"code": "13703", "description": "Q4 2025 Cycle"},
]

# Insert data directly with SQLite
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we already have data to avoid duplicates
    cursor.execute("SELECT COUNT(*) FROM cycles")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Table already contains {count} records. Skipping insertion.")
    else:
        for cycle in cycle_codes:
            cursor.execute(
                "INSERT INTO cycles (code, description) VALUES (?, ?)",
                (cycle["code"], cycle["description"])
            )
        
        conn.commit()
        print(f"Added {len(cycle_codes)} cycle codes to the database.")
    
    # Verify data
    cursor.execute("SELECT * FROM cycles")
    rows = cursor.fetchall()
    print("\nCycles in the database:")
    for row in rows:
        print(f"ID: {row[0]}, Code: {row[1]}, Description: {row[2]}")
    
    conn.close()
except Exception as e:
    print(f"Error inserting data: {str(e)}")
    if 'conn' in locals():
        conn.close()

print("\nDone! The Cycles table has been created and populated with test data.")
print("You can now use this table for your dynamic dropdown in the Resource Counts Summary report.")