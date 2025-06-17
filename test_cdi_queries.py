#!/usr/bin/env python3
"""
Test script to diagnose CDI variable database queries and SQLAlchemy relationships
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from app.datawarehouse.models import DealCdiVarRpt, TrancheBal, Deal, Tranche
from app.datawarehouse.dao import get_dw_db

def test_cdi_database_queries():
    """Test CDI variable database queries step by step"""
    
    print("=" * 80)
    print("CDI VARIABLE DATABASE DIAGNOSTIC TEST")
    print("=" * 80)
    
    # Get database session
    db = next(get_dw_db())
    
    try:
        # Test 1: Basic CDI variable count
        print("\n1. BASIC CDI VARIABLE COUNT")
        print("-" * 40)
        
        total_cdi_vars = db.query(DealCdiVarRpt).count()
        print(f"Total CDI variables in database: {total_cdi_vars}")
        
        if total_cdi_vars == 0:
            print("❌ NO CDI VARIABLES FOUND! Database might be empty.")
            return
        
        # Test 2: Sample CDI variables
        print("\n2. SAMPLE CDI VARIABLES")
        print("-" * 40)
        
        sample_cdi_vars = db.query(DealCdiVarRpt).limit(5).all()
        for i, var in enumerate(sample_cdi_vars, 1):
            print(f"Sample {i}:")
            print(f"  Deal: {var.dl_nbr}")
            print(f"  Cycle: {var.cycle_cde}")
            print(f"  Variable Name: '{var.dl_cdi_var_nme}' (length: {len(var.dl_cdi_var_nme)})")
            print(f"  Variable Name Trimmed: '{var.dl_cdi_var_nme.strip()}'")
            print(f"  Variable Value: {var.dl_cdi_var_value}")
            print(f"  Numeric Value: {var.numeric_value}")
            print()
        
        # Test 3: Tranche balance count
        print("\n3. TRANCHE BALANCE COUNT")
        print("-" * 40)
        
        total_tranches = db.query(TrancheBal).count()
        print(f"Total tranche balances in database: {total_tranches}")
        
        if total_tranches == 0:
            print("❌ NO TRANCHE BALANCES FOUND!")
            return
        
        # Test 4: Sample tranche balances
        print("\n4. SAMPLE TRANCHE BALANCES")
        print("-" * 40)
        
        sample_tranches = db.query(TrancheBal).limit(5).all()
        for i, tranche in enumerate(sample_tranches, 1):
            print(f"Sample {i}:")
            print(f"  Deal: {tranche.dl_nbr}")
            print(f"  Tranche ID: '{tranche.tr_id}' (length: {len(tranche.tr_id)})")
            print(f"  Tranche ID Trimmed: '{tranche.tr_id.strip()}'")
            print(f"  Cycle: {tranche.cycle_cde}")
            print(f"  Balance: {tranche.tr_end_bal_amt}")
            print()
        
        # Test 5: Find deals that have both CDI vars and tranche data
        print("\n5. DEALS WITH BOTH CDI VARS AND TRANCHE DATA")
        print("-" * 40)
        
        deals_with_both = db.query(
            DealCdiVarRpt.dl_nbr.distinct()
        ).join(
            TrancheBal, 
            (DealCdiVarRpt.dl_nbr == TrancheBal.dl_nbr) & 
            (DealCdiVarRpt.cycle_cde == TrancheBal.cycle_cde)
        ).limit(3).all()
        
        print(f"Found {len(deals_with_both)} deals with both CDI vars and tranche data:")
        for deal_nbr, in deals_with_both:
            print(f"  Deal: {deal_nbr}")
        
        if not deals_with_both:
            print("❌ NO DEALS FOUND WITH BOTH CDI VARS AND TRANCHE DATA!")
            return
        
        # Test 6: Test a specific deal in detail
        test_deal = deals_with_both[0][0]
        print(f"\n6. DETAILED ANALYSIS OF DEAL {test_deal}")
        print("-" * 40)
        
        # Get CDI variables for this deal
        deal_cdi_vars = db.query(DealCdiVarRpt).filter(
            DealCdiVarRpt.dl_nbr == test_deal
        ).all()
        
        print(f"CDI variables for deal {test_deal}: {len(deal_cdi_vars)}")
        for var in deal_cdi_vars[:3]:  # Show first 3
            print(f"  Variable: '{var.dl_cdi_var_nme.strip()}' = {var.dl_cdi_var_value}")
        
        # Get tranche balances for this deal
        deal_tranches = db.query(TrancheBal).filter(
            TrancheBal.dl_nbr == test_deal
        ).all()
        
        print(f"Tranche balances for deal {test_deal}: {len(deal_tranches)}")
        for tranche in deal_tranches[:3]:  # Show first 3
            print(f"  Tranche: '{tranche.tr_id.strip()}' (cycle {tranche.cycle_cde}) = ${tranche.tr_end_bal_amt}")
        
        # Test 7: Test the problematic query pattern
        print(f"\n7. TESTING CDI-TRANCHE JOIN FOR DEAL {test_deal}")
        print("-" * 40)
        
        # First, let's see what cycles are available
        cycles_in_deal = db.query(TrancheBal.cycle_cde.distinct()).filter(
            TrancheBal.dl_nbr == test_deal
        ).all()
        print(f"Available cycles for deal {test_deal}: {[c[0] for c in cycles_in_deal]}")
        
        if cycles_in_deal:
            test_cycle = cycles_in_deal[0][0]
            print(f"Testing with cycle: {test_cycle}")
            
            # Test the join that was failing
            join_results = db.query(
                DealCdiVarRpt,
                TrancheBal
            ).join(
                TrancheBal,
                (DealCdiVarRpt.dl_nbr == TrancheBal.dl_nbr) &
                (DealCdiVarRpt.cycle_cde == TrancheBal.cycle_cde)
            ).filter(
                DealCdiVarRpt.dl_nbr == test_deal,
                DealCdiVarRpt.cycle_cde == test_cycle
            ).limit(5).all()
            
            print(f"Join results: {len(join_results)}")
            for cdi_var, tranche_bal in join_results[:2]:
                print(f"  CDI: '{cdi_var.dl_cdi_var_nme.strip()}' -> Tranche: '{tranche_bal.tr_id.strip()}'")
        
        # Test 8: Test specific tranche ID matching
        print(f"\n8. TESTING TRANCHE ID MATCHING")
        print("-" * 40)
        
        # Get a sample tranche ID
        if deal_tranches:
            sample_tranche = deal_tranches[0]
            sample_tr_id = sample_tranche.tr_id.strip()
            sample_cycle = sample_tranche.cycle_cde
            
            print(f"Testing tranche ID matching for: '{sample_tr_id}' in cycle {sample_cycle}")
            
            # Test direct match (this should work)
            direct_match = db.query(TrancheBal).filter(
                TrancheBal.dl_nbr == test_deal,
                TrancheBal.cycle_cde == sample_cycle,
                TrancheBal.tr_id == sample_tranche.tr_id  # Use exact padded version
            ).count()
            print(f"Direct match (with padding): {direct_match}")
            
            # Test trimmed match
            trimmed_match = db.query(TrancheBal).filter(
                TrancheBal.dl_nbr == test_deal,
                TrancheBal.cycle_cde == sample_cycle,
                func.trim(TrancheBal.tr_id) == sample_tr_id  # Use trimmed version
            ).count()
            print(f"Trimmed match: {trimmed_match}")
            
            # Test IN clause with multiple formats
            test_tr_ids = [
                sample_tr_id,  # Clean version
                sample_tr_id.ljust(15),  # Padded to 15
                sample_tr_id.ljust(20),  # Padded to 20
                sample_tranche.tr_id  # Original padded version
            ]
            
            in_clause_match = db.query(TrancheBal).filter(
                TrancheBal.dl_nbr == test_deal,
                TrancheBal.cycle_cde == sample_cycle,
                TrancheBal.tr_id.in_(test_tr_ids)
            ).count()
            print(f"IN clause match (multiple formats): {in_clause_match}")
        
        # Test 9: Test CDI variable name patterns
        print(f"\n9. CDI VARIABLE NAME PATTERNS")
        print("-" * 40)
        
        # Look for common patterns
        rri_vars = db.query(DealCdiVarRpt).filter(
            DealCdiVarRpt.dl_cdi_var_nme.like('%RRI%')
        ).limit(3).all()
        
        print(f"Variables containing 'RRI': {len(rri_vars)}")
        for var in rri_vars:
            print(f"  '{var.dl_cdi_var_nme.strip()}' (deal {var.dl_nbr}, cycle {var.cycle_cde})")
        
        # Test 10: Test the actual tranche mapping logic
        print(f"\n10. TESTING TRANCHE MAPPING LOGIC")
        print("-" * 40)
        
        # Simulate the problematic tranche mapping
        test_mappings = {
            "B1": ["1B1", "2B1", "B1"],
            "M1": ["1M1", "2M1", "M1"]
        }
        
        for suffix, tr_id_list in test_mappings.items():
            print(f"Testing mapping {suffix} -> {tr_id_list}")
            
            # Find tranches that match this mapping
            matching_tranches = db.query(TrancheBal).filter(
                TrancheBal.dl_nbr == test_deal,
                func.trim(TrancheBal.tr_id).in_(tr_id_list)
            ).all()
            
            print(f"  Found {len(matching_tranches)} matching tranches:")
            for tranche in matching_tranches[:2]:
                print(f"    '{tranche.tr_id.strip()}' (cycle {tranche.cycle_cde})")
        
        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_raw_sql_queries():
    """Test using raw SQL to understand the data structure"""
    
    print("\n" + "=" * 80)
    print("RAW SQL DIAGNOSTIC TEST")
    print("=" * 80)
    
    db = next(get_dw_db())
    
    try:
        # Test the table structure
        print("\n1. DEAL_CDI_VAR_RPT TABLE STRUCTURE")
        print("-" * 40)
        
        # Check if the table exists and get some info about it
        result = db.execute(text("""
            SELECT 
                dl_nbr,
                dl_cdi_var_nme,
                LENGTH(dl_cdi_var_nme) as name_length,
                dl_cdi_var_value,
                cycle_cde
            FROM deal_cdi_var_rpt 
            LIMIT 3
        """)).fetchall()
        
        for row in result:
            print(f"Deal: {row[0]}, Variable: '{row[1]}' (len={row[2]}), Value: {row[3]}, Cycle: {row[4]}")
        
        print("\n2. TRANCHEBAL TABLE STRUCTURE")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                dl_nbr,
                tr_id,
                LENGTH(tr_id) as tr_id_length,
                cycle_cde,
                tr_end_bal_amt
            FROM tranchebal 
            LIMIT 3
        """)).fetchall()
        
        for row in result:
            print(f"Deal: {row[0]}, Tranche: '{row[1]}' (len={row[2]}), Cycle: {row[3]}, Balance: {row[4]}")
        
        print("\n3. JOIN TEST WITH RAW SQL")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                c.dl_nbr,
                c.cycle_cde,
                TRIM(c.dl_cdi_var_nme) as variable_name,
                TRIM(t.tr_id) as tranche_id,
                c.dl_cdi_var_value,
                t.tr_end_bal_amt
            FROM deal_cdi_var_rpt c
            INNER JOIN tranchebal t ON c.dl_nbr = t.dl_nbr AND c.cycle_cde = t.cycle_cde
            WHERE c.dl_cdi_var_nme LIKE '%RRI%'
                AND TRIM(t.tr_id) IN ('1B1', '2B1', 'B1', '1M1', '2M1', 'M1')
            LIMIT 5
        """)).fetchall()
        
        print(f"Raw SQL join results: {len(result)} rows")
        for row in result:
            print(f"  Deal {row[0]}, Cycle {row[1]}: '{row[2]}' -> Tranche '{row[3]}' = {row[4]}")
    
    except Exception as e:
        print(f"❌ ERROR in raw SQL test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting CDI Database Diagnostic Tests...")
    test_cdi_database_queries()
    test_raw_sql_queries()
    print("\nDiagnostic tests complete!")