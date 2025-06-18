#!/usr/bin/env python3
"""
Script to populate static field calculations based on database schema.
This creates SYSTEM_FIELD type calculations for all available database fields.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, get_dw_db
from app.calculations.models import Calculation, CalculationType, GroupLevel
from app.calculations.service import UnifiedCalculationService
from app.calculations.schemas import SystemFieldCalculationCreate
from sqlalchemy import text
import sqlite3


def get_table_schema(db_path: str):
    """Get schema information from the datawarehouse database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema = {}
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    
    for table_name in tables:
        if table_name in ['deal', 'tranche', 'tranchebal']:
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            schema[table_name] = []
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_nullable = not bool(col[3])
                
                schema[table_name].append({
                    'name': col_name,
                    'type': col_type,
                    'nullable': is_nullable
                })
    
    conn.close()
    return schema


def determine_field_type(sql_type: str) -> str:
    """Map SQL types to field types."""
    sql_type = sql_type.upper()
    
    if 'CHAR' in sql_type or 'VARCHAR' in sql_type or 'TEXT' in sql_type:
        return 'string'
    elif 'INTEGER' in sql_type or 'SMALLINT' in sql_type:
        return 'number'
    elif 'NUMERIC' in sql_type and 'DECIMAL' in sql_type:
        return 'currency'
    elif 'FLOAT' in sql_type or 'REAL' in sql_type:
        return 'number'
    elif 'DATE' in sql_type:
        return 'date'
    elif 'BOOLEAN' in sql_type:
        return 'boolean'
    else:
        return 'string'


def create_friendly_name(table_name: str, field_name: str) -> str:
    """Create user-friendly names for fields."""
    
    # Special mappings for known CDI fields
    name_mappings = {
        'deal.cdi_file_nme': 'CDI File Name',
        'deal.CDB_cdi_file_nme': 'CDB CDI File Name',
        'deal.dl_nbr': 'Deal Number',
        'deal.issr_cde': 'Issuer Code',
        'tranche.dl_nbr': 'Tranche Deal Number',
        'tranche.tr_id': 'Tranche ID',
        'tranche.tr_cusip_id': 'Tranche CUSIP',
        'tranchebal.dl_nbr': 'Tranche Balance Deal Number',
        'tranchebal.tr_id': 'Tranche Balance ID',
        'tranchebal.cycle_cde': 'Cycle Code',
        'tranchebal.tr_end_bal_amt': 'Ending Balance Amount',
        'tranchebal.tr_pass_thru_rte': 'Pass Through Rate',
        'tranchebal.tr_prin_rel_ls_amt': 'Principal Release Amount',
        'tranchebal.tr_int_dstrb_amt': 'Interest Distribution Amount',
        'tranchebal.tr_prin_dstrb_amt': 'Principal Distribution Amount',
        'tranchebal.tr_int_accrl_amt': 'Interest Accrual Amount',
        'tranchebal.tr_accrl_days': 'Accrual Days',
        'tranchebal.tr_int_shtfl_amt': 'Interest Shortfall Amount',
    }
    
    field_path = f"{table_name}.{field_name}"
    if field_path in name_mappings:
        return name_mappings[field_path]
    
    # For unmapped fields, include table context to ensure uniqueness
    table_prefix = {
        'deal': 'Deal',
        'tranche': 'Tranche',
        'tranchebal': 'Balance'
    }.get(table_name, table_name.capitalize())
    
    # Generate generic friendly name with table context
    field_words = field_name.replace('_', ' ').split()
    field_title = ' '.join(word.capitalize() for word in field_words)
    
    return f"{table_prefix} {field_title}"


def create_friendly_description(table_name: str, field_name: str) -> str:
    """Create user-friendly descriptions for fields."""
    
    description_mappings = {
        'deal.cdi_file_nme': 'CDI file name associated with the deal',
        'deal.CDB_cdi_file_nme': 'CDB CDI file name for the deal',
        'deal.dl_nbr': 'Unique deal identifier number',
        'deal.issr_cde': 'Issuer code identifying the deal issuer',
        'tranche.tr_id': 'Tranche identifier within the deal',
        'tranche.tr_cusip_id': 'CUSIP identifier for the tranche',
        'tranchebal.tr_end_bal_amt': 'Ending balance amount for the tranche',
        'tranchebal.tr_pass_thru_rte': 'Pass through rate for the tranche',
        'tranchebal.tr_prin_rel_ls_amt': 'Principal release loss amount',
        'tranchebal.tr_int_dstrb_amt': 'Interest distribution amount',
        'tranchebal.tr_prin_dstrb_amt': 'Principal distribution amount',
        'tranchebal.tr_int_accrl_amt': 'Interest accrual amount',
        'tranchebal.tr_accrl_days': 'Number of accrual days',
        'tranchebal.cycle_cde': 'Cycle code for the reporting period',
    }
    
    field_path = f"{table_name}.{field_name}"
    if field_path in description_mappings:
        return description_mappings[field_path]
    
    return f"{field_name.replace('_', ' ').title()} from {table_name} table"


def determine_group_level(table_name: str) -> GroupLevel:
    """Determine the appropriate group level for a field."""
    if table_name in ['tranche', 'tranchebal']:
        return GroupLevel.TRANCHE
    else:
        return GroupLevel.DEAL


def main():
    """Main function to populate static field calculations."""
    
    print("🚀 Starting static field calculation population...")
    
    # Get database schema
    dw_db_path = "vibez_datawarehouse.db" 
    schema = get_table_schema(dw_db_path)
    
    print(f"📊 Found tables: {list(schema.keys())}")
    
    # Create database sessions
    config_db = SessionLocal()
    dw_db = next(get_dw_db())
    
    try:
        # Check existing calculations to avoid duplicates
        existing_calculations = config_db.query(Calculation).filter(
            Calculation.calculation_type == CalculationType.SYSTEM_FIELD
        ).all()
        
        existing_field_paths = set()
        for calc in existing_calculations:
            if calc.metadata_config and 'field_path' in calc.metadata_config:
                existing_field_paths.add(calc.metadata_config['field_path'])
        
        print(f"📋 Found {len(existing_field_paths)} existing static field calculations")
        
        # Initialize calculation service
        calc_service = UnifiedCalculationService(config_db, dw_db)
        
        created_count = 0
        skipped_count = 0
        
        # Process each table and field
        for table_name, columns in schema.items():
            print(f"\n📊 Processing table: {table_name}")
            
            for column in columns:
                field_name = column['name']
                field_path = f"{table_name}.{field_name}"
                
                # Skip if already exists
                if field_path in existing_field_paths:
                    print(f"  ⏭️  Skipping existing field: {field_path}")
                    skipped_count += 1
                    continue
                
                try:
                    # Create the static field calculation
                    calc_data = SystemFieldCalculationCreate(
                        name=create_friendly_name(table_name, field_name),
                        description=create_friendly_description(table_name, field_name),
                        field_path=field_path,
                        group_level=determine_group_level(table_name),
                        metadata_config={
                            'field_path': field_path,
                            'field_type': determine_field_type(column['type']),
                            'nullable': column['nullable'],
                            'sql_type': column['type']
                        }
                    )
                    
                    created_calc = calc_service.create_system_field_calculation(calc_data, "system")
                    print(f"  ✅ Created: {created_calc.name} (ID: {created_calc.id})")
                    created_count += 1
                    
                except Exception as e:
                    print(f"  ❌ Error creating {field_path}: {str(e)}")
        
        print(f"\n🎉 Completed!")
        print(f"   Created: {created_count} new static field calculations")
        print(f"   Skipped: {skipped_count} existing calculations")
        print(f"   Total: {created_count + skipped_count + len(existing_field_paths)} static field calculations")
        
    except Exception as e:
        config_db.rollback()
        print(f"❌ Error in main process: {str(e)}")
        raise
    finally:
        config_db.close()
        dw_db.close()


if __name__ == "__main__":
    main()