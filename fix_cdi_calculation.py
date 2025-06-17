#!/usr/bin/env python3
"""
Fix script for CDI variable calculation issues
Run this to fix the Investment Field calculation
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def fix_cdi_calculation():
    """Fix the Investment Field CDI calculation"""
    
    from app.core.database import SessionLocal, get_dw_db
    from app.calculations.service import SystemCalculationService
    from app.calculations.dao import SystemCalculationDAO
    from app.calculations.cdi_service import CDIVariableCalculationService
    from app.calculations.cdi_schemas import CDIVariableUpdate
    
    print("=" * 80)
    print("CDI CALCULATION FIX - Investment Field")
    print("=" * 80)
    
    # Create database sessions
    config_db = SessionLocal()
    dw_db = next(get_dw_db())
    
    try:
        # Initialize services
        system_calc_dao = SystemCalculationDAO(config_db)
        system_calc_service = SystemCalculationService(system_calc_dao)
        cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
        
        print("\n1. FIXING TRANCHE MAPPINGS")
        print("-" * 50)
        
        # Fixed tranche mappings (adding missing 2M1 and proper padding)
        fixed_tranche_mappings = {
            "M1": ["1M1", "2M1", "M1", "1M1            ", "2M1            ", "M1             "],  # Added padded versions
            "M2": ["1M2", "2M2", "M2", "1M2            ", "2M2            ", "M2             "],  # Added padded versions
            "B1": ["1B1", "2B1", "B1", "1B1            ", "2B1            ", "B1             "],  # Added padded versions
            "B2": ["B2", "1B2", "2B2", "B2             ", "1B2            ", "2B2            "],  # Added padded versions
            "B1_INV": ["1B1_INV", "2B1_INV", "1B1_INV        ", "2B1_INV        "],  # Added padded versions
            "M1_INV": ["1M1_INV", "1M1_INV        "],  # Added padded versions
            "M2_INV": ["1M2_INV", "1M2_INV        "],  # Added padded versions
            "A1_INV": ["1A1_INV", "1A1_INV        "],  # Added padded versions
            "1M2": ["1M2", "1M2            "],  # Added padded versions
            "2M2": ["2M2", "2M2            "],  # Added padded versions
            "1B1": ["1B1", "1B1            "],  # Added padded versions
            "2B1": ["2B1", "2B1            "]   # Added padded versions
        }
        
        # Update the calculation
        update_request = CDIVariableUpdate(
            tranche_mappings=fixed_tranche_mappings
        )
        
        try:
            updated_calc = cdi_service.update_cdi_variable_calculation(1, update_request)
            print("✅ Successfully updated tranche mappings!")
            print(f"   Calculation: {updated_calc.name}")
            print(f"   Updated mappings: {len(fixed_tranche_mappings)} suffix mappings")
            
            # Show the M1 fix specifically
            print(f"   M1 mapping fixed: {fixed_tranche_mappings['M1']}")
            
        except Exception as e:
            print(f"❌ Failed to update calculation: {str(e)}")
            return
        
        print("\n2. TESTING FIXED CALCULATION")
        print("-" * 50)
        
        # Test the fixed calculation
        sample_cycle = 12503
        sample_deals = [426123001]
        
        try:
            result_df = cdi_service.execute_cdi_variable_calculation(1, sample_cycle, sample_deals)
            print(f"✅ Execution test successful! Returned {len(result_df)} rows")
            
            if len(result_df) > 0:
                print("Sample results:")
                print(result_df.head().to_string())
            else:
                print("⚠️  Still returning 0 rows - need to investigate data further")
                
        except Exception as e:
            print(f"❌ Execution test failed: {str(e)}")
        
        print("\n3. TESTING SQL PREVIEW")
        print("-" * 50)
        
        try:
            sql_preview = cdi_service.generate_cdi_sql_preview(1, sample_cycle, sample_deals)
            print("✅ SQL preview working!")
            print("First 500 characters of generated SQL:")
            print(sql_preview['sql'][:500] + "...")
            
        except Exception as e:
            print(f"❌ SQL preview failed: {str(e)}")
        
        print("\n4. VERIFYING DATABASE UPDATE")
        print("-" * 50)
        
        # Verify the update was saved
        system_calc = system_calc_service.get_system_calculation_by_id(1)
        if system_calc and system_calc.metadata_config:
            updated_mappings = system_calc.metadata_config.get("tranche_mappings", {})
            m1_mapping = updated_mappings.get("M1", [])
            
            if "2M1" in m1_mapping:
                print("✅ Database update verified - M1 mapping now includes 2M1")
            else:
                print("❌ Database update failed - M1 mapping still missing 2M1")
        
        print("\n" + "=" * 80)
        print("FIX COMPLETE")
        print("=" * 80)
        print("Next steps:")
        print("1. Test the calculation in your web UI")
        print("2. Check that SQL preview now appears")
        print("3. Verify that reports show actual values instead of blank columns")
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        config_db.close()
        dw_db.close()

if __name__ == "__main__":
    fix_cdi_calculation()