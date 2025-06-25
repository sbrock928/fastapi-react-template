#!/usr/bin/env python3
"""Script to create comprehensive sample data for the Deal & Tranche system."""

import sys
import os
from decimal import Decimal
from datetime import date

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import DWSessionLocal
from app.datawarehouse.models import Deal, Tranche, TrancheBal, DealCdiVarRpt


def create_comprehensive_sample_data():
    """Create a comprehensive set of sample deals and tranches."""

    dw_db = DWSessionLocal()

    try:
        # Clear existing data first
        print("Clearing existing data...")
        dw_db.query(DealCdiVarRpt).delete()
        dw_db.query(TrancheBal).delete()
        dw_db.query(Tranche).delete()
        dw_db.query(Deal).delete()
        dw_db.commit()

        print("Creating comprehensive sample data...")

        # Sample deals with new schema structure
        deals_data = [
            # Original test deals
            {
                "dl_nbr": 1001,
                "issr_cde": "GSAMP2024",
                "cdi_file_nme": "GS24001A",
                "CDB_cdi_file_nme": "GS24001CDB",
            },
            {
                "dl_nbr": 1002,
                "issr_cde": "WFCM2024A",
                "cdi_file_nme": "WF24002A",
                "CDB_cdi_file_nme": "WF24002CDB",
            },
            {
                "dl_nbr": 1003,
                "issr_cde": "CHAR2024",
                "cdi_file_nme": "CH24003A",
                "CDB_cdi_file_nme": "CH24003CDB",
            },
            # Investment SQL specific deals
            {
                "dl_nbr": 426121001,
                "issr_cde": "INVT2024A",
                "cdi_file_nme": "INV426121001",
                "CDB_cdi_file_nme": "INV426121001CDB",
            },
            {
                "dl_nbr": 426121002,
                "issr_cde": "INVT2024B",
                "cdi_file_nme": "INV426121002",
                "CDB_cdi_file_nme": "INV426121002CDB",
            },
        ]

        # Create deals
        created_deals = []
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
            created_deals.append(deal)

        dw_db.flush()  # Flush to get IDs but don't commit yet

        # Define tranches for each deal
        tranches_data = []

        # Original test deals tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1001, "tr_id": "A1", "tr_cusip_id": "GSAMP2024A1001"},
                {"dl_nbr": 1001, "tr_id": "A2", "tr_cusip_id": "GSAMP2024A2001"},
                {"dl_nbr": 1001, "tr_id": "B", "tr_cusip_id": "GSAMP2024B0001"},
                {"dl_nbr": 1002, "tr_id": "A", "tr_cusip_id": "WFCM2024A0002"},
                {"dl_nbr": 1002, "tr_id": "B", "tr_cusip_id": "WFCM2024B0002"},
                {"dl_nbr": 1003, "tr_id": "A", "tr_cusip_id": "CHAR2024A0003"},
                {"dl_nbr": 1003, "tr_id": "B", "tr_cusip_id": "CHAR2024B0003"},
            ]
        )

        # Investment SQL specific tranches for deal 426121001
        tranches_data.extend(
            [
                {"dl_nbr": 426121001, "tr_id": "1M1", "tr_cusip_id": "INVT20241M1001"},
                {"dl_nbr": 426121001, "tr_id": "2M1", "tr_cusip_id": "INVT20242M1001"},
                {"dl_nbr": 426121001, "tr_id": "M1", "tr_cusip_id": "INVT2024M1001"},
                {"dl_nbr": 426121001, "tr_id": "1M2", "tr_cusip_id": "INVT20241M2001"},
                {"dl_nbr": 426121001, "tr_id": "2M2", "tr_cusip_id": "INVT20242M2001"},
                {"dl_nbr": 426121001, "tr_id": "M2", "tr_cusip_id": "INVT2024M2001"},
                {"dl_nbr": 426121001, "tr_id": "1B1", "tr_cusip_id": "INVT20241B1001"},
                {"dl_nbr": 426121001, "tr_id": "2B1", "tr_cusip_id": "INVT20242B1001"},
                {"dl_nbr": 426121001, "tr_id": "B1", "tr_cusip_id": "INVT2024B1001"},
                {"dl_nbr": 426121001, "tr_id": "B2", "tr_cusip_id": "INVT2024B2001"},
                {"dl_nbr": 426121001, "tr_id": "1B2", "tr_cusip_id": "INVT20241B2001"},
                {"dl_nbr": 426121001, "tr_id": "2B2", "tr_cusip_id": "INVT20242B2001"},
                {"dl_nbr": 426121001, "tr_id": "1B1_INV", "tr_cusip_id": "INVT20241B1INV001"},
                {"dl_nbr": 426121001, "tr_id": "2B1_INV", "tr_cusip_id": "INVT20242B1INV001"},
                {"dl_nbr": 426121001, "tr_id": "1M1_INV", "tr_cusip_id": "INVT20241M1INV001"},
                {"dl_nbr": 426121001, "tr_id": "1M2_INV", "tr_cusip_id": "INVT20241M2INV001"},
                {"dl_nbr": 426121001, "tr_id": "1A1_INV", "tr_cusip_id": "INVT20241A1INV001"},
            ]
        )

        # Investment SQL specific tranches for deal 426121002
        tranches_data.extend(
            [
                {"dl_nbr": 426121002, "tr_id": "1M1", "tr_cusip_id": "INVT20241M1002"},
                {"dl_nbr": 426121002, "tr_id": "2M1", "tr_cusip_id": "INVT20242M1002"},
                {"dl_nbr": 426121002, "tr_id": "M1", "tr_cusip_id": "INVT2024M1002"},
                {"dl_nbr": 426121002, "tr_id": "1M2", "tr_cusip_id": "INVT20241M2002"},
                {"dl_nbr": 426121002, "tr_id": "2M2", "tr_cusip_id": "INVT20242M2002"},
                {"dl_nbr": 426121002, "tr_id": "M2", "tr_cusip_id": "INVT2024M2002"},
                {"dl_nbr": 426121002, "tr_id": "1B1", "tr_cusip_id": "INVT20241B1002"},
                {"dl_nbr": 426121002, "tr_id": "2B1", "tr_cusip_id": "INVT20242B1002"},
                {"dl_nbr": 426121002, "tr_id": "B1", "tr_cusip_id": "INVT2024B1002"},
                {"dl_nbr": 426121002, "tr_id": "B2", "tr_cusip_id": "INVT2024B2002"},
                {"dl_nbr": 426121002, "tr_id": "1B2", "tr_cusip_id": "INVT20241B2002"},
                {"dl_nbr": 426121002, "tr_id": "2B2", "tr_cusip_id": "INVT20242B2002"},
                {"dl_nbr": 426121002, "tr_id": "1B1_INV", "tr_cusip_id": "INVT20241B1INV002"},
                {"dl_nbr": 426121002, "tr_id": "2B1_INV", "tr_cusip_id": "INVT20242B1INV002"},
                {"dl_nbr": 426121002, "tr_id": "1M1_INV", "tr_cusip_id": "INVT20241M1INV002"},
                {"dl_nbr": 426121002, "tr_id": "1M2_INV", "tr_cusip_id": "INVT20241M2INV002"},
                {"dl_nbr": 426121002, "tr_id": "1A1_INV", "tr_cusip_id": "INVT20241A1INV002"},
            ]
        )

        # Create tranches
        created_tranches = []
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)
            created_tranches.append(tranche)

        dw_db.flush()

        # Create TrancheBal records for both cycles
        tranche_bal_data = []
        cycles = [202404, 12506]  # Regular cycle and investment SQL cycle

        for cycle in cycles:
            for tranche in created_tranches:
                import random

                base_balance = random.uniform(10_000_000, 100_000_000)  # $10M to $100M

                tranche_bal_data.append(
                    {
                        "dl_nbr": tranche.dl_nbr,
                        "tr_id": tranche.tr_id,
                        "cycle_cde": cycle,
                        "tr_end_bal_amt": round(base_balance, 2),
                        "tr_prin_rel_ls_amt": round(base_balance * 0.05, 2),
                        "tr_pass_thru_rte": round(random.uniform(0.02, 0.08), 6),
                        "tr_accrl_days": 30,
                        "tr_int_dstrb_amt": round(base_balance * 0.003, 2),
                        "tr_prin_dstrb_amt": round(base_balance * 0.02, 2),
                        "tr_int_accrl_amt": round(base_balance * 0.0025, 2),
                        "tr_int_shtfl_amt": round(base_balance * 0.0001, 2),
                    }
                )

        # Create tranche balances
        for bal_data in tranche_bal_data:
            tranche_bal = TrancheBal(**bal_data)
            dw_db.add(tranche_bal)

        dw_db.flush()

        # Create CDI Variable data for Investment SQL
        cdi_var_data = []
        import random

        # CDI variable names from your SQL
        cdi_variables = [
            "#RPT_RRI_M1                 ",
            "#RPT_RRI_M2                 ",
            "#RPT_RRI_B1                 ",
            "#RPT_RRI_B2                 ",
            "#RPT_RRI_1M2                ",
            "#RPT_RRI_2M2                ",
            "#RPT_RRI_1B1                ",
            "#RPT_RRI_2B1                ",
            "#RPT_RRI_A1                 ",
        ]

        # Create CDI data for both investment deals
        for deal_nbr in [426121001, 426121002]:
            for var_name in cdi_variables:
                # Generate realistic investment income values
                base_value = random.uniform(50000, 500000)  # $50K to $500K

                cdi_var_data.append(
                    {
                        "dl_nbr": deal_nbr,
                        "cycle_cde": 12506,
                        "dl_cdi_var_nme": var_name,
                        "dl_cdi_var_value": round(base_value, 2),
                    }
                )

        # Create CDI variable records
        for cdi_data in cdi_var_data:
            cdi_var = DealCdiVarRpt(**cdi_data)
            dw_db.add(cdi_var)

        # Commit all changes
        dw_db.commit()

        print(f"✅ Successfully created sample data:")
        print(f"   📊 {len(created_deals)} deals")
        print(f"   📈 {len(created_tranches)} tranches")
        print(f"   📊 {len(tranche_bal_data)} tranche balance records")
        print(f"   📋 {len(cdi_var_data)} CDI variable records")

        # Print deal summary
        print(f"\n📋 Created deals:")
        for deal in created_deals:
            print(f"   Deal {deal.dl_nbr}: {deal.issr_cde}")

        print(f"\n💰 Investment SQL specific data:")
        print(f"   Deals: 426121001, 426121002")
        print(f"   Cycle: 12506")
        print(f"   CDI Variables: {len(cdi_variables)}")

        return True

    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating sample data: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        dw_db.close()


def main():
    """Main function to run the sample data creation."""
    print("🚀 Creating comprehensive sample data for Deal & Tranche system...")

    success = create_comprehensive_sample_data()

    if success:
        print("\n🎉 Sample data creation completed successfully!")
        print("\n🔗 You can now test the APIs:")
        print("   curl http://localhost:8000/api/reports/data/deals")
        print("   curl http://localhost:8000/api/reports/data/deals/1001/tranches")
    else:
        print("\n❌ Sample data creation failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
