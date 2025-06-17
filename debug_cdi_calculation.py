#!/usr/bin/env python3
"""
Debug script for CDI variable calculation issues
Run this to diagnose and test your CDI calculation
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_cdi_calculation_debug():
    """Debug the specific CDI calculation from your work database"""
    
    from app.core.database import SessionLocal, get_dw_db
    from app.calculations.service import SystemCalculationService
    from app.calculations.dao import SystemCalculationDAO
    from app.calculations.cdi_service import CDIVariableCalculationService
    from app.datawarehouse.models import DealCdiVarRpt, TrancheBal
    from sqlalchemy import func
    
    print("=" * 80)
    print("CDI CALCULATION DEBUG - Investment Field")
    print("=" * 80)
    
    # Create database sessions
    config_db = SessionLocal()
    dw_db = next(get_dw_db())
    
    try:
        # Initialize services
        system_calc_dao = SystemCalculationDAO(config_db)
        system_calc_service = SystemCalculationService(system_calc_dao)
        cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
        
        print("\n1. CHECKING CDI CALCULATION METADATA")
        print("-" * 50)
        
        # Get the calculation
        system_calc = system_calc_service.get_system_calculation_by_id(1)
        if not system_calc:
            print("❌ Calculation with ID 1 not found!")
            return
        
        print(f"✅ Found calculation: {system_calc.name}")
        print(f"   Result column: {system_calc.result_column_name}")
        print(f"   Group level: {system_calc.group_level}")
        print(f"   Is CDI variable: {cdi_service._is_cdi_variable_calculation(system_calc)}")
        
        if not cdi_service._is_cdi_variable_calculation(system_calc):
            print("❌ This is not recognized as a CDI variable calculation!")
            return
        
        metadata = system_calc.metadata_config
        variable_pattern = metadata["variable_pattern"]
        tranche_mappings = metadata["tranche_mappings"]
        
        print(f"   Variable pattern: {variable_pattern}")
        print(f"   Tranche mappings: {len(tranche_mappings)} suffix mappings")
        
        print("\n2. TESTING SAMPLE DATA AVAILABILITY")
        print("-" * 50)
        
        # Test with sample data
        sample_cycle = 12503  # Use a cycle from your data
        sample_deals = [426123001]  # Use deal from your data
        
        print(f"Testing with cycle {sample_cycle} and deals {sample_deals}")
        
        # Check if CDI variables exist for this pattern
        total_cdi_count = dw_db.query(DealCdiVarRpt).filter(
            DealCdiVarRpt.cycle_cde == sample_cycle,
            DealCdiVarRpt.dl_nbr.in_(sample_deals)
        ).count()
        
        print(f"Total CDI variables in cycle {sample_cycle}: {total_cdi_count}")
        
        # Check for RRI variables specifically
        rri_count = dw_db.query(DealCdiVarRpt).filter(
            DealCdiVarRpt.cycle_cde == sample_cycle,
            DealCdiVarRpt.dl_nbr.in_(sample_deals),
            DealCdiVarRpt.dl_cdi_var_nme.like('%RRI%')
        ).count()
        
        print(f"RRI-related variables: {rri_count}")
        
        if rri_count > 0:
            # Show sample RRI variables
            sample_rri = dw_db.query(DealCdiVarRpt).filter(
                DealCdiVarRpt.cycle_cde == sample_cycle,
                DealCdiVarRpt.dl_nbr.in_(sample_deals),
                DealCdiVarRpt.dl_cdi_var_nme.like('%RRI%')
            ).limit(3).all()
            
            print("Sample RRI variables found:")
            for var in sample_rri:
                print(f"  '{var.dl_cdi_var_nme.strip()}' = {var.dl_cdi_var_value}")
        
        print("\n3. TESTING TRANCHE MAPPING LOGIC")
        print("-" * 50)
        
        # Test each tranche suffix mapping
        for suffix, tr_id_list in tranche_mappings.items():
            variable_name = variable_pattern.replace("{tranche_suffix}", suffix)
            print(f"\nTesting suffix '{suffix}' -> variable '{variable_name}'")
            print(f"  Mapped to tranches: {tr_id_list}")
            
            # Check if CDI variable exists
            cdi_var_count = dw_db.query(DealCdiVarRpt).filter(
                DealCdiVarRpt.cycle_cde == sample_cycle,
                DealCdiVarRpt.dl_nbr.in_(sample_deals),
                DealCdiVarRpt.dl_cdi_var_nme == variable_name.ljust(32)
            ).count()
            
            print(f"  CDI variable matches: {cdi_var_count}")
            
            if cdi_var_count > 0:
                # Check tranche matches
                tranche_matches = dw_db.query(TrancheBal).filter(
                    TrancheBal.cycle_cde == sample_cycle,
                    TrancheBal.dl_nbr.in_(sample_deals),
                    func.trim(TrancheBal.tr_id).in_(tr_id_list)
                ).count()
                
                print(f"  Tranche matches: {tranche_matches}")
        
        print("\n4. TESTING ACTUAL EXECUTION")
        print("-" * 50)
        
        try:
            result_df = cdi_service.execute_cdi_variable_calculation(1, sample_cycle, sample_deals)
            print(f"✅ Execution successful! Returned {len(result_df)} rows")
            
            if len(result_df) > 0:
                print("Sample results:")
                print(result_df.head().to_string())
            else:
                print("⚠️  Execution returned 0 rows - this is the problem!")
                
        except Exception as e:
            print(f"❌ Execution failed: {str(e)}")
            
        print("\n5. TESTING SQL PREVIEW")
        print("-" * 50)
        
        try:
            sql_preview = cdi_service.generate_cdi_sql_preview(1, sample_cycle, sample_deals)
            print("✅ SQL preview generated successfully!")
            print("Generated SQL:")
            print(sql_preview['sql'])
            
        except Exception as e:
            print(f"❌ SQL preview failed: {str(e)}")
        
        print("\n6. RECOMMENDED FIXES")
        print("-" * 50)
        
        # Check for missing 2M1 mapping
        m1_mapping = tranche_mappings.get("M1", [])
        if "2M1" not in m1_mapping:
            print("🔧 FIX NEEDED: M1 mapping is missing '2M1'")
            print(f"   Current M1 mapping: {m1_mapping}")
            print(f"   Should be: ['1M1', '2M1', 'M1']")
        
        # Check if any variables actually exist for the pattern
        pattern_variables = []
        for suffix in tranche_mappings.keys():
            var_name = variable_pattern.replace("{tranche_suffix}", suffix)
            exists = dw_db.query(DealCdiVarRpt).filter(
                DealCdiVarRpt.dl_cdi_var_nme == var_name.ljust(32)
            ).first()
            if exists:
                pattern_variables.append((suffix, var_name.strip()))
        
        if pattern_variables:
            print(f"✅ Found {len(pattern_variables)} matching variables:")
            for suffix, var_name in pattern_variables[:5]:  # Show first 5
                print(f"   {suffix} -> {var_name}")
        else:
            print("⚠️  No variables found matching the pattern - check variable names in database")
    
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        config_db.close()
        dw_db.close()

if __name__ == "__main__":
    test_cdi_calculation_debug()