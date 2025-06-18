#!/usr/bin/env python3
"""
Comprehensive test data seeding script for calculation builders
Creates extensive deals, tranches, tranchebal, and CDI variable data
"""

import sqlite3
import random
from decimal import Decimal
from datetime import datetime, timedelta

def seed_comprehensive_test_data():
    """Seed comprehensive test data for all calculation builders"""
    
    # Connect to databases
    config_db = sqlite3.connect('vibez_config.db')
    dw_db = sqlite3.connect('vibez_datawarehouse.db')
    
    try:
        print("🌱 Starting comprehensive test data seeding...")
        
        # Seed configuration database
        seed_config_data(config_db)
        
        # Seed datawarehouse with extensive data
        seed_datawarehouse_data(dw_db)
        
        print("✅ Comprehensive test data seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding test data: {e}")
        raise
    finally:
        config_db.close()
        dw_db.close()

def seed_config_data(db):
    """Seed configuration database with sample calculations"""
    cursor = db.cursor()
    
    print("📊 Seeding configuration database...")
    
    # Clear existing data
    cursor.execute("DELETE FROM calculations")
    
    # Sample user calculations
    user_calculations = [
        (1, "Total Ending Balance", "Sum of all ending balances", "user_aggregation", "SUM", "TrancheBal", "tr_end_bal_amt", None, "deal", "admin", None, 1),
        (2, "Average Pass Through Rate", "Average pass through rate across tranches", "user_aggregation", "AVG", "TrancheBal", "tr_pass_thru_rte", None, "tranche", "admin", None, 1),
        (3, "Weighted Average PTR", "Weighted average pass through rate by balance", "user_aggregation", "WEIGHTED_AVG", "TrancheBal", "tr_pass_thru_rte", "tr_end_bal_amt", "deal", "admin", None, 1),
        (4, "Deal Count", "Count of unique deals", "user_aggregation", "COUNT", "Deal", "dl_nbr", None, "deal", "admin", None, 1),
        (5, "Max Ending Balance", "Maximum ending balance amount", "user_aggregation", "MAX", "TrancheBal", "tr_end_bal_amt", None, "deal", "admin", None, 1),
    ]
    
    cursor.executemany("""
        INSERT INTO calculations (
            id, name, description, calculation_type, aggregation_function, 
            source_model, source_field, weight_field, group_level, 
            created_by, approved_by, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, user_calculations)
    
    # System calculations (these should already exist from your previous data)
    print("✅ Configuration database seeded")
    db.commit()

def seed_datawarehouse_data(db):
    """Seed datawarehouse with comprehensive test data"""
    cursor = db.cursor()
    
    print("🏭 Seeding datawarehouse with comprehensive data...")
    
    # Clear existing data
    cursor.execute("DELETE FROM deal_cdi_var_rpt")
    cursor.execute("DELETE FROM tranchebal")
    cursor.execute("DELETE FROM tranche")
    cursor.execute("DELETE FROM deal")
    
    # Seed deals (50 deals with diverse issuer types)
    deals = []
    issuer_types = [
        "BANK_OF_AMERICA", "BANK_WELLS_FARGO", "BANK_CHASE", "BANK_CITIGROUP",
        "CREDIT_UNION_NAVY", "CREDIT_UNION_STATE", "CREDIT_UNION_TEACHERS",
        "MORTGAGE_CORP", "FINANCIAL_SERVICES", "INVESTMENT_BANK", "HEDGE_FUND",
        "INSURANCE_COMPANY", "PENSION_FUND", "SOVEREIGN_WEALTH", "REAL_ESTATE"
    ]
    
    for i in range(1, 51):  # Deal numbers 1-50
        deal_id = i * 100  # 100, 200, 300, ..., 5000
        issuer = random.choice(issuer_types)
        deals.append((
            deal_id,
            issuer,
            f"CDI_FILE_{deal_id}.xml",
            f"CDB_CDI_FILE_{deal_id}.xml"
        ))
    
    cursor.executemany("""
        INSERT INTO deal (dl_nbr, issr_cde, cdi_file_nme, CDB_cdi_file_nme)
        VALUES (?, ?, ?, ?)
    """, deals)
    
    # Seed tranches (multiple tranches per deal)
    tranches = []
    tranche_types = [
        'A', 'B', 'C', 'D',  # Senior tranches
        'M1', 'M2', 'M3',    # Mezzanine tranches
        'B1', 'B2', 'B3',    # Subordinate tranches
        '1A1', '2A1', '1A2', '2A2',  # Sub-tranches
        '1M1', '2M1', '1M2', '2M2',  # Mezzanine sub-tranches
        '1B1', '2B1', '1B2', '2B2',  # Subordinate sub-tranches
        '1A1_INV', '1B1_INV', '1M1_INV',  # Investment tranches
        '2B1_INV', '2A1_INV'
    ]
    
    for deal_id in range(100, 5100, 100):  # For each deal
        # Each deal gets 8-15 random tranches
        num_tranches = random.randint(8, 15)
        selected_tranches = random.sample(tranche_types, num_tranches)
        
        for tr_id in selected_tranches:
            tranches.append((
                deal_id,
                tr_id,
                f"{deal_id}{tr_id}CUSIP{random.randint(100, 999)}"
            ))
    
    cursor.executemany("""
        INSERT INTO tranche (dl_nbr, tr_id, tr_cusip_id)
        VALUES (?, ?, ?)
    """, tranches)
    
    # Seed tranche balances (multiple cycles per tranche)
    tranche_balances = []
    cycles = [1, 2, 3, 4, 5, 202401, 202402, 202403, 202404, 202405]
    
    # Get all existing tranches
    cursor.execute("SELECT dl_nbr, tr_id FROM tranche")
    existing_tranches = cursor.fetchall()
    
    for dl_nbr, tr_id in existing_tranches:
        for cycle in cycles:
            # Generate realistic balance amounts
            base_amount = random.randint(5_000_000, 500_000_000)  # $5M to $500M
            
            # Vary amounts by cycle (simulate amortization)
            cycle_factor = 1.0
            if cycle > 1:
                cycle_factor = 1.0 - (cycle - 1) * 0.05  # 5% reduction per cycle
            
            ending_balance = int(base_amount * cycle_factor)
            
            # Pass through rates vary by tranche type
            if tr_id.startswith('A'):
                ptr_rate = round(random.uniform(0.02, 0.04), 6)  # Senior: 2-4%
            elif tr_id.startswith('M'):
                ptr_rate = round(random.uniform(0.04, 0.07), 6)  # Mezz: 4-7%
            elif tr_id.startswith('B'):
                ptr_rate = round(random.uniform(0.07, 0.12), 6)  # Sub: 7-12%
            else:
                ptr_rate = round(random.uniform(0.03, 0.08), 6)  # Other: 3-8%
            
            # Generate other required fields
            prin_rel_ls_amt = round(random.uniform(0, ending_balance * 0.1), 2)  # 0-10% of balance
            accrl_days = random.randint(28, 31)  # Days in month
            int_dstrb_amt = round(random.uniform(0, ending_balance * 0.01), 2)  # 0-1% of balance
            prin_dstrb_amt = round(random.uniform(0, ending_balance * 0.05), 2)  # 0-5% of balance
            int_accrl_amt = round(random.uniform(0, ending_balance * 0.005), 2)  # 0-0.5% of balance
            int_shtfl_amt = round(random.uniform(0, ending_balance * 0.002), 2)  # 0-0.2% of balance
            
            tranche_balances.append((
                dl_nbr,
                tr_id,
                cycle,
                ending_balance,
                prin_rel_ls_amt,
                ptr_rate,
                accrl_days,
                int_dstrb_amt,
                prin_dstrb_amt,
                int_accrl_amt,
                int_shtfl_amt
            ))
    
    cursor.executemany("""
        INSERT INTO tranchebal (
            dl_nbr, tr_id, cycle_cde, tr_end_bal_amt, tr_prin_rel_ls_amt, 
            tr_pass_thru_rte, tr_accrl_days, tr_int_dstrb_amt, 
            tr_prin_dstrb_amt, tr_int_accrl_amt, tr_int_shtfl_amt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tranche_balances)
    
    # Seed CDI variables (comprehensive set matching your query needs)
    cdi_variables = []
    
    # CDI variable patterns that match your Investment Income calculation
    cdi_patterns = [
        '#RPT_RRI_M1                 ',
        '#RPT_RRI_M2                 ',
        '#RPT_RRI_B1                 ',
        '#RPT_RRI_B2                 ',
        '#RPT_RRI_A1                 ',
        '#RPT_RRI_1M1                ',
        '#RPT_RRI_1M2                ',
        '#RPT_RRI_2M1                ',
        '#RPT_RRI_2M2                ',
        '#RPT_RRI_1B1                ',
        '#RPT_RRI_1B2                ',
        '#RPT_RRI_2B1                ',
        '#RPT_RRI_2B2                ',
        '#RPT_EXC_M1                 ',
        '#RPT_EXC_M2                 ',
        '#RPT_EXC_B1                 ',
        '#RPT_EXC_B2                 ',
        '#RPT_FEES_M1                ',
        '#RPT_FEES_M2                ',
        '#RPT_FEES_B1                ',
        '#RPT_FEES_B2                ',
        '#RPT_DEAL_TOTAL             ',
        '#RPT_DEAL_STATUS            ',
        '#RPT_PRINCIPAL_M1           ',
        '#RPT_PRINCIPAL_M2           ',
        '#RPT_PRINCIPAL_B1           ',
        '#RPT_PRINCIPAL_B2           '
    ]
    
    for deal_id in range(100, 5100, 100):  # For each deal
        for cycle in cycles:
            for var_name in cdi_patterns:
                # Generate realistic CDI values based on variable type
                if 'RRI' in var_name:  # Investment income
                    value = round(random.uniform(50000, 2000000), 2)  # $50K to $2M
                elif 'EXC' in var_name:  # Excess interest
                    value = round(random.uniform(10000, 500000), 2)  # $10K to $500K
                elif 'FEES' in var_name:  # Fees
                    value = round(random.uniform(5000, 100000), 2)  # $5K to $100K
                elif 'TOTAL' in var_name:  # Deal totals
                    value = round(random.uniform(1000000, 50000000), 2)  # $1M to $50M
                elif 'PRINCIPAL' in var_name:  # Principal payments
                    value = round(random.uniform(100000, 10000000), 2)  # $100K to $10M
                else:
                    value = round(random.uniform(1000, 1000000), 2)  # Default range
                
                cdi_variables.append((
                    deal_id,
                    cycle,
                    var_name,
                    str(value)
                ))
    
    cursor.executemany("""
        INSERT INTO deal_cdi_var_rpt (dl_nbr, cycle_cde, dl_cdi_var_nme, dl_cdi_var_value)
        VALUES (?, ?, ?, ?)
    """, cdi_variables)
    
    # Add some additional test-specific data for your exact query
    test_deals = [100, 200, 300, 400, 500]
    test_tranches = ['A', 'B', '1M1', '2M1', 'M1', '1M2', '2M2', 'M2', '1B1', '2B1', 'B1', 'B2', '1B2', '2B2', '1B1_INV', '2B1_INV', '1M1_INV', '1M2_INV', '1A1_INV']
    
    # Ensure these specific combinations exist
    for deal_id in test_deals:
        for tr_id in test_tranches:
            # Add tranche if not exists
            cursor.execute("INSERT OR IGNORE INTO tranche (dl_nbr, tr_id, tr_cusip_id) VALUES (?, ?, ?)",
                          (deal_id, tr_id, f"{deal_id}{tr_id}TESTCUSIP"))
            
            # Add tranche balance for cycle 1 with all required fields
            balance_amt = random.randint(1000000, 50000000)
            cursor.execute("""
                INSERT OR REPLACE INTO tranchebal (
                    dl_nbr, tr_id, cycle_cde, tr_end_bal_amt, tr_prin_rel_ls_amt, 
                    tr_pass_thru_rte, tr_accrl_days, tr_int_dstrb_amt, 
                    tr_prin_dstrb_amt, tr_int_accrl_amt, tr_int_shtfl_amt
                ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal_id, tr_id, balance_amt, 
                round(random.uniform(0, balance_amt * 0.1), 2),  # prin_rel_ls_amt
                round(random.uniform(0.02, 0.10), 6),  # pass_thru_rte
                30,  # accrl_days
                round(random.uniform(0, balance_amt * 0.01), 2),  # int_dstrb_amt
                round(random.uniform(0, balance_amt * 0.05), 2),  # prin_dstrb_amt
                round(random.uniform(0, balance_amt * 0.005), 2),  # int_accrl_amt
                round(random.uniform(0, balance_amt * 0.002), 2)   # int_shtfl_amt
            ))
            
            # Add corresponding CDI variables
            for var_pattern in ['#RPT_RRI_M1                 ', '#RPT_RRI_M2                 ', '#RPT_RRI_B1                 ', '#RPT_RRI_1M2                ', '#RPT_RRI_2M2                ', '#RPT_RRI_1B1                ', '#RPT_RRI_2B1                ']:
                cursor.execute("""
                    INSERT OR REPLACE INTO deal_cdi_var_rpt (dl_nbr, cycle_cde, dl_cdi_var_nme, dl_cdi_var_value)
                    VALUES (?, 1, ?, ?)
                """, (deal_id, var_pattern, str(round(random.uniform(100000, 1000000), 2))))
    
    print(f"✅ Seeded {len(deals)} deals")
    print(f"✅ Seeded {len(tranches)} tranches")
    print(f"✅ Seeded {len(tranche_balances)} tranche balances")
    print(f"✅ Seeded {len(cdi_variables)} CDI variables")
    
    db.commit()

def print_data_summary():
    """Print summary of seeded data"""
    config_db = sqlite3.connect('vibez_config.db')
    dw_db = sqlite3.connect('vibez_datawarehouse.db')
    
    try:
        print("\n📈 Data Summary:")
        print("=" * 50)
        
        # Config database counts
        config_cursor = config_db.cursor()
        config_cursor.execute("SELECT COUNT(*) FROM calculations WHERE calculation_type = 'user_aggregation'")
        user_calc_count = config_cursor.fetchone()[0]
        
        config_cursor.execute("SELECT COUNT(*) FROM calculations WHERE calculation_type = 'system_sql'")
        system_calc_count = config_cursor.fetchone()[0]
        
        print(f"📊 Configuration Database:")
        print(f"   - User Calculations: {user_calc_count}")
        print(f"   - System Calculations: {system_calc_count}")
        
        # Datawarehouse counts
        dw_cursor = dw_db.cursor()
        
        dw_cursor.execute("SELECT COUNT(*) FROM deal")
        deal_count = dw_cursor.fetchone()[0]
        
        dw_cursor.execute("SELECT COUNT(*) FROM tranche")
        tranche_count = dw_cursor.fetchone()[0]
        
        dw_cursor.execute("SELECT COUNT(*) FROM tranchebal")
        balance_count = dw_cursor.fetchone()[0]
        
        dw_cursor.execute("SELECT COUNT(*) FROM deal_cdi_var_rpt")
        cdi_count = dw_cursor.fetchone()[0]
        
        dw_cursor.execute("SELECT COUNT(DISTINCT cycle_cde) FROM tranchebal")
        cycle_count = dw_cursor.fetchone()[0]
        
        print(f"🏭 Datawarehouse:")
        print(f"   - Deals: {deal_count}")
        print(f"   - Tranches: {tranche_count}")
        print(f"   - Tranche Balances: {balance_count}")
        print(f"   - CDI Variables: {cdi_count}")
        print(f"   - Cycles: {cycle_count}")
        
        # Sample data for testing
        print(f"\n🧪 Sample Test Data:")
        dw_cursor.execute("""
            SELECT dl_nbr, COUNT(DISTINCT tr_id) as tranche_count 
            FROM tranche 
            WHERE dl_nbr IN (100, 200, 300, 400, 500)
            GROUP BY dl_nbr
            ORDER BY dl_nbr
        """)
        
        for deal_id, tr_count in dw_cursor.fetchall():
            print(f"   - Deal {deal_id}: {tr_count} tranches")
        
        # CDI variable sample
        dw_cursor.execute("""
            SELECT dl_cdi_var_nme, COUNT(*) as count
            FROM deal_cdi_var_rpt 
            WHERE dl_nbr IN (100, 200, 300) AND cycle_cde = 1
            GROUP BY dl_cdi_var_nme
            ORDER BY dl_cdi_var_nme
            LIMIT 10
        """)
        
        print(f"\n📊 Sample CDI Variables (Cycle 1, Deals 100-300):")
        for var_name, count in dw_cursor.fetchall():
            print(f"   - {var_name.strip()}: {count} records")
        
    finally:
        config_db.close()
        dw_db.close()

if __name__ == "__main__":
    seed_comprehensive_test_data()
    print_data_summary()
    print("\n🎉 Ready for comprehensive testing!")
    print("\nNow you can:")
    print("1. Test user-defined calculations with various aggregation functions")
    print("2. Test system SQL calculations with complex CTEs")
    print("3. Test CDI variable calculations with tranche mappings")
    print("4. Generate reports with multiple calculation types")
    print("5. Test with different cycles and deal/tranche combinations")