# scripts/setup_datawarehouse_cdi_data.py
"""
Comprehensive data seeding script for the datawarehouse.
Creates extensive test data including deals, tranches, tranche balances, and CDI variables
across multiple cycles for robust testing of the CDI calculation system.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random
from decimal import Decimal

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_dw_db
from app.datawarehouse.models import Deal, Tranche, TrancheBal, DealCdiVarRpt
from sqlalchemy.sql import func


def create_comprehensive_test_data():
    """Create comprehensive test data for the datawarehouse"""
    
    dw_db = next(get_dw_db())
    
    try:
        # Check if extensive data already exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 10:  # Allow recreation if we only have sample data
            print(f"Extensive data already exists ({existing_deals} deals found). Use --force to recreate.")
            return
        
        print("🚀 Creating comprehensive datawarehouse test data...")
        
        # Configuration
        NUM_DEALS = 50
        CYCLES = [1, 2, 3, 4, 5, 6]  # 6 different cycles
        ISSUER_TYPES = ["BANK", "CREDIT", "FINANCE", "MORTGAGE", "AUTO", "STUDENT"]
        TRANCHE_TYPES = {
            "A": {"rating": "AAA", "seniority": 1, "typical_balance": 2000000},
            "B": {"rating": "AA", "seniority": 2, "typical_balance": 1000000},
            "M1": {"rating": "A", "seniority": 3, "typical_balance": 800000},
            "M2": {"rating": "BBB", "seniority": 4, "typical_balance": 500000},
            "B1": {"rating": "BB", "seniority": 5, "typical_balance": 300000},
            "B2": {"rating": "B", "seniority": 6, "typical_balance": 200000},
        }
        
        created_deals = []
        created_tranches = []
        created_tranche_bals = []
        created_cdi_vars = []
        
        # ===== CREATE DEALS =====
        print("Creating deals...")
        for deal_num in range(1000, 1000 + NUM_DEALS):
            issuer_type = random.choice(ISSUER_TYPES)
            deal = Deal(
                dl_nbr=deal_num,
                issr_cde=f"{issuer_type}{deal_num:02d}",
                cdi_file_nme=f"D{deal_num}",
                CDB_cdi_file_nme=f"CDB{deal_num}"
            )
            created_deals.append(deal)
        
        dw_db.add_all(created_deals)
        dw_db.flush()
        print(f"✅ Created {len(created_deals)} deals")
        
        # ===== CREATE TRANCHES =====
        print("Creating tranches...")
        for deal in created_deals:
            # Each deal gets 3-6 random tranches
            num_tranches = random.randint(3, 6)
            selected_tranches = random.sample(list(TRANCHE_TYPES.keys()), num_tranches)
            
            for tr_id in selected_tranches:
                tranche = Tranche(
                    dl_nbr=deal.dl_nbr,
                    tr_id=tr_id,
                    tr_cusip_id=f"{deal.dl_nbr}{tr_id}000"
                )
                created_tranches.append(tranche)
        
        dw_db.add_all(created_tranches)
        dw_db.flush()
        print(f"✅ Created {len(created_tranches)} tranches")
        
        # ===== CREATE TRANCHE BALANCES =====
        print("Creating tranche balances...")
        for cycle in CYCLES:
            cycle_balances = []
            
            for tranche in created_tranches:
                tranche_info = TRANCHE_TYPES[tranche.tr_id]
                base_balance = tranche_info["typical_balance"]
                
                # Add some randomness and cycle progression
                cycle_factor = 1.0 - (cycle - 1) * 0.08  # Balances decrease over time
                random_factor = random.uniform(0.7, 1.3)  # ±30% variation
                
                ending_balance = int(base_balance * cycle_factor * random_factor)
                principal_release = int(ending_balance * random.uniform(0.02, 0.08))  # 2-8% principal
                pass_thru_rate = random.uniform(0.025, 0.065)  # 2.5% - 6.5%
                
                # Calculate other fields based on ending balance
                interest_dist = int(ending_balance * pass_thru_rate / 12)  # Monthly interest
                principal_dist = principal_release
                interest_accrual = interest_dist
                interest_shortfall = int(interest_dist * random.uniform(0, 0.1))  # 0-10% shortfall
                
                tranche_bal = TrancheBal(
                    dl_nbr=tranche.dl_nbr,
                    tr_id=tranche.tr_id,
                    cycle_cde=cycle,
                    tr_end_bal_amt=ending_balance,
                    tr_prin_rel_ls_amt=principal_release,
                    tr_pass_thru_rte=pass_thru_rate,
                    tr_accrl_days=30,
                    tr_int_dstrb_amt=interest_dist,
                    tr_prin_dstrb_amt=principal_dist,
                    tr_int_accrl_amt=interest_accrual,
                    tr_int_shtfl_amt=interest_shortfall
                )
                cycle_balances.append(tranche_bal)
            
            created_tranche_bals.extend(cycle_balances)
        
        # Batch insert tranche balances
        batch_size = 1000
        for i in range(0, len(created_tranche_bals), batch_size):
            batch = created_tranche_bals[i:i + batch_size]
            dw_db.add_all(batch)
            dw_db.flush()
            print(f"  Inserted batch {i//batch_size + 1} ({len(batch)} records)")
        
        print(f"✅ Created {len(created_tranche_bals)} tranche balance records")
        
        # ===== CREATE CDI VARIABLES =====
        print("Creating CDI variables...")
        
        # CDI Variable patterns that match your calculations
        cdi_patterns = {
            "#RPT_RRI_": "investment_income",    # Revenue Recognition Income
            "#RPT_EXC_": "excess_interest",      # Excess Interest
            "#RPT_FEES_": "servicing_fees",      # Servicing Fees
            "#RPT_PRINC_": "principal_payments", # Principal Payments
            "#RPT_INT_": "interest_payments"     # Interest Payments
        }
        
        # Deal-level CDI variable patterns (NEW)
        deal_level_patterns = {
            "#RPT_DEAL_TOTAL_PRINCIPAL": "deal_summary",
            "#RPT_DEAL_TOTAL_INTEREST": "deal_summary", 
            "#RPT_DEAL_PAYMENT_DATE": "deal_payment_info",
            "#RPT_DEAL_STATUS": "deal_status",
            "#RPT_DEAL_SERVICER_FEE": "deal_summary",
            "#RPT_DEAL_NET_INCOME": "deal_summary",
            "#RPT_DEAL_EXCESS_SPREAD": "deal_summary",
            "#RPT_DEAL_MATURITY_DATE": "deal_payment_info",
            "#RPT_DEAL_RATING": "deal_status"
        }
        
        current_time = func.now()
        
        for cycle in CYCLES:
            cycle_cdi_vars = []
            
            for deal in created_deals:
                # Get tranches for this deal
                deal_tranches = [t for t in created_tranches if t.dl_nbr == deal.dl_nbr]
                
                # ===== CREATE DEAL-LEVEL CDI VARIABLES (NEW) =====
                # Calculate deal totals from tranche balances
                deal_total_balance = sum(
                    tb.tr_end_bal_amt for tb in created_tranche_bals 
                    if tb.dl_nbr == deal.dl_nbr and tb.cycle_cde == cycle
                )
                deal_total_interest = sum(
                    tb.tr_int_dstrb_amt for tb in created_tranche_bals 
                    if tb.dl_nbr == deal.dl_nbr and tb.cycle_cde == cycle
                )
                deal_total_principal = sum(
                    tb.tr_prin_dstrb_amt for tb in created_tranche_bals 
                    if tb.dl_nbr == deal.dl_nbr and tb.cycle_cde == cycle
                )
                
                for var_name, var_type in deal_level_patterns.items():
                    if var_type == "deal_summary":
                        if "PRINCIPAL" in var_name:
                            value = deal_total_principal * random.uniform(0.95, 1.05)
                        elif "INTEREST" in var_name:
                            value = deal_total_interest * random.uniform(0.95, 1.05)
                        elif "SERVICER_FEE" in var_name:
                            value = deal_total_balance * 0.005 * random.uniform(0.8, 1.2)  # 0.5% servicing fee
                        elif "NET_INCOME" in var_name:
                            value = deal_total_interest * random.uniform(1.1, 1.3)  # Income > interest
                        elif "EXCESS_SPREAD" in var_name:
                            value = deal_total_interest * random.uniform(0.1, 0.25)  # 10-25% excess
                        else:
                            value = deal_total_balance * random.uniform(0.01, 0.05)
                    elif var_type == "deal_payment_info":
                        if "DATE" in var_name:
                            # Generate payment date as YYYYMMDD format
                            base_date = datetime(2024, 1, 15) + timedelta(days=cycle*30)
                            value = int(base_date.strftime("%Y%m%d"))
                        else:
                            value = random.uniform(1000, 10000)
                    elif var_type == "deal_status":
                        if "RATING" in var_name:
                            # Generate numeric rating (1-10)
                            value = random.randint(1, 10)
                        elif "STATUS" in var_name:
                            # Generate status code (1=Active, 2=Maturing, 3=Closed)
                            status_codes = [1, 1, 1, 2, 3]  # Weighted toward Active
                            value = random.choice(status_codes)
                        else:
                            value = random.randint(1, 5)
                    else:
                        value = random.uniform(1000, 50000)
                    
                    cdi_var = DealCdiVarRpt(
                        dl_nbr=deal.dl_nbr,
                        cycle_cde=cycle,
                        dl_cdi_var_nme=var_name.ljust(32),  # Pad to CHAR(32)
                        dl_cdi_var_value=f"{value:.2f}".ljust(32),  # Pad to CHAR(32)
                        lst_upd_dtm=current_time,
                        lst_upd_user_id='data_seeder',
                        lst_upd_host_nme='localhost'
                    )
                    cycle_cdi_vars.append(cdi_var)
                
                # ===== CREATE TRANCHE-LEVEL CDI VARIABLES (EXISTING) =====
                for pattern_prefix, var_type in cdi_patterns.items():
                    for tranche in deal_tranches:
                        # Create both specific tranche ID and generic patterns
                        tranche_suffixes = [tranche.tr_id]  # Exact tranche ID
                        
                        # Add some mapped suffixes for testing complex mappings
                        if tranche.tr_id == "A":
                            tranche_suffixes.extend(["1A1", "2A1"])
                        elif tranche.tr_id == "B":
                            tranche_suffixes.extend(["1B1", "2B1"])
                        elif tranche.tr_id == "M1":
                            tranche_suffixes.extend(["1M1", "2M1"])
                        elif tranche.tr_id == "M2":
                            tranche_suffixes.extend(["1M2", "2M2"])
                        
                        for suffix in tranche_suffixes:
                            var_name = f"{pattern_prefix}{suffix}"
                            
                            # Generate realistic values based on tranche balance
                            tranche_bal = next((tb for tb in created_tranche_bals 
                                              if tb.dl_nbr == deal.dl_nbr and 
                                                 tb.tr_id == tranche.tr_id and 
                                                 tb.cycle_cde == cycle), None)
                            
                            if tranche_bal:
                                if var_type == "investment_income":
                                    value = tranche_bal.tr_int_dstrb_amt * random.uniform(1.1, 1.5)
                                elif var_type == "excess_interest":
                                    value = tranche_bal.tr_int_dstrb_amt * random.uniform(0.1, 0.3)
                                elif var_type == "servicing_fees":
                                    value = tranche_bal.tr_end_bal_amt * 0.005 * random.uniform(0.8, 1.2)
                                elif var_type == "principal_payments":
                                    value = tranche_bal.tr_prin_dstrb_amt * random.uniform(0.95, 1.05)
                                elif var_type == "interest_payments":
                                    value = tranche_bal.tr_int_dstrb_amt * random.uniform(0.95, 1.05)
                                else:
                                    value = random.uniform(1000, 50000)
                                
                                cdi_var = DealCdiVarRpt(
                                    dl_nbr=deal.dl_nbr,
                                    cycle_cde=cycle,
                                    dl_cdi_var_nme=var_name.ljust(32),  # Pad to CHAR(32)
                                    dl_cdi_var_value=f"{value:.2f}".ljust(32),  # Pad to CHAR(32)
                                    lst_upd_dtm=current_time,
                                    lst_upd_user_id='data_seeder',
                                    lst_upd_host_nme='localhost'
                                )
                                cycle_cdi_vars.append(cdi_var)
            
            created_cdi_vars.extend(cycle_cdi_vars)
        
        # Batch insert CDI variables
        for i in range(0, len(created_cdi_vars), batch_size):
            batch = created_cdi_vars[i:i + batch_size]
            dw_db.add_all(batch)
            dw_db.flush()
            print(f"  Inserted CDI batch {i//batch_size + 1} ({len(batch)} records)")
        
        print(f"✅ Created {len(created_cdi_vars)} CDI variable records")
        
        # ===== COMMIT ALL CHANGES =====
        dw_db.commit()
        
        # ===== SUMMARY =====
        print("\n🎉 Comprehensive test data creation completed!")
        print("=" * 60)
        print(f"📊 Data Summary:")
        print(f"   • Deals: {len(created_deals)}")
        print(f"   • Tranches: {len(created_tranches)}")
        print(f"   • Tranche Balances: {len(created_tranche_bals)}")
        print(f"   • CDI Variables: {len(created_cdi_vars)}")
        print(f"   • Cycles: {len(CYCLES)} ({min(CYCLES)} - {max(CYCLES)})")
        print(f"   • Deal Range: {min(d.dl_nbr for d in created_deals)} - {max(d.dl_nbr for d in created_deals)}")
        
        print(f"\n📈 Sample Deal Breakdown:")
        sample_deals = random.sample(created_deals, min(5, len(created_deals)))
        for deal in sample_deals:
            deal_tranches = [t.tr_id for t in created_tranches if t.dl_nbr == deal.dl_nbr]
            print(f"   • Deal {deal.dl_nbr} ({deal.issr_cde}): {len(deal_tranches)} tranches ({', '.join(deal_tranches)})")
        
        print(f"\n🔧 CDI Variable Patterns Created:")
        for pattern, desc in cdi_patterns.items():
            pattern_count = len([v for v in created_cdi_vars if v.variable_name.startswith(pattern.strip())])
            print(f"   • {pattern}* ({desc}): {pattern_count} variables")
        
        # Show deal-level patterns (NEW)
        print(f"\n🏢 Deal-Level CDI Variables Created:")
        for pattern, desc in deal_level_patterns.items():
            pattern_count = len([v for v in created_cdi_vars if v.variable_name.strip() == pattern])
            print(f"   • {pattern} ({desc}): {pattern_count} variables")
        
        print(f"\n✅ Ready for Testing:")
        print(f"   • Test CDI calculations with cycle codes: {CYCLES}")
        print(f"   • Use deal numbers: {min(d.dl_nbr for d in created_deals)}-{max(d.dl_nbr for d in created_deals)}")
        print(f"   • Available tranche types: {', '.join(TRANCHE_TYPES.keys())}")
        print(f"   • Deal-level variables: {len(deal_level_patterns)} patterns per deal")
        print(f"   • Tranche-level variables: {len(cdi_patterns)} patterns per tranche")
        
    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating comprehensive test data: {str(e)}")
        raise
    finally:
        dw_db.close()


def clear_existing_data():
    """Clear all existing datawarehouse data (use with caution!)"""
    dw_db = next(get_dw_db())
    
    try:
        print("🗑️ Clearing existing datawarehouse data...")
        
        # Delete in reverse dependency order
        dw_db.query(DealCdiVarRpt).delete()
        dw_db.query(TrancheBal).delete()
        dw_db.query(Tranche).delete()
        dw_db.query(Deal).delete()
        
        dw_db.commit()
        print("✅ All existing data cleared")
        
    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error clearing data: {str(e)}")
        raise
    finally:
        dw_db.close()


def show_data_summary():
    """Show summary of current datawarehouse data"""
    dw_db = next(get_dw_db())
    
    try:
        print("\n📊 Current Datawarehouse Summary:")
        print("=" * 50)
        
        deal_count = dw_db.query(Deal).count()
        tranche_count = dw_db.query(Tranche).count()
        tranche_bal_count = dw_db.query(TrancheBal).count()
        cdi_var_count = dw_db.query(DealCdiVarRpt).count()
        
        print(f"Deals: {deal_count}")
        print(f"Tranches: {tranche_count}")
        print(f"Tranche Balances: {tranche_bal_count}")
        print(f"CDI Variables: {cdi_var_count}")
        
        if deal_count > 0:
            # Show deal ranges
            deals = dw_db.query(Deal.dl_nbr).all()
            deal_numbers = [d[0] for d in deals]
            print(f"Deal Range: {min(deal_numbers)} - {max(deal_numbers)}")
            
            # Show cycles
            cycles = dw_db.query(TrancheBal.cycle_cde.distinct()).all()
            if cycles:
                cycle_numbers = sorted([c[0] for c in cycles])
                print(f"Available Cycles: {cycle_numbers}")
            
            # Show tranche types
            tranche_types = dw_db.query(Tranche.tr_id.distinct()).all()
            if tranche_types:
                tr_ids = sorted([t[0] for t in tranche_types])
                print(f"Tranche Types: {tr_ids}")
        
    except Exception as e:
        print(f"❌ Error showing summary: {str(e)}")
    finally:
        dw_db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Datawarehouse data seeding utility")
    parser.add_argument("--clear", action="store_true", help="Clear all existing data first")
    parser.add_argument("--force", action="store_true", help="Force recreation even if data exists")
    parser.add_argument("--summary", action="store_true", help="Show data summary only")
    
    args = parser.parse_args()
    
    if args.summary:
        show_data_summary()
    elif args.clear:
        clear_existing_data()
        if not args.summary:
            create_comprehensive_test_data()
    else:
        create_comprehensive_test_data()