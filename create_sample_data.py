#!/usr/bin/env python3
"""Script to create comprehensive sample data for the Deal & Tranche system."""

import sys
import os
from decimal import Decimal
from datetime import date

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import DWSessionLocal
from app.datawarehouse.models import Deal, Tranche, TrancheBal


def create_comprehensive_sample_data():
    """Create a comprehensive set of sample deals and tranches."""

    dw_db = DWSessionLocal()

    try:
        # Check if sample data already exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 0:
            print(f"Sample data already exists ({existing_deals} deals found). Skipping creation.")
            return

        print("Creating comprehensive sample data...")

        # Sample deals with new schema structure
        deals_data = [
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
            {
                "dl_nbr": 1004,
                "issr_cde": "BOARMBS24",
                "cdi_file_nme": "BA24004A",
                "CDB_cdi_file_nme": "BA24004CDB",
            },
            {
                "dl_nbr": 1005,
                "issr_cde": "CITSL24A",
                "cdi_file_nme": "CT24005A",
                "CDB_cdi_file_nme": "CT24005CDB",
            },
            {
                "dl_nbr": 1006,
                "issr_cde": "MSCMBS24",
                "cdi_file_nme": "MS24006A",
                "CDB_cdi_file_nme": "MS24006CDB",
            },
        ]

        # Create deals
        created_deals = []
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
            created_deals.append(deal)

        dw_db.flush()  # Flush to get IDs but don't commit yet

        # Define tranches for each deal using new schema
        tranches_data = []

        # Deal 1001 tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1001, "tr_id": "A1"},
                {"dl_nbr": 1001, "tr_id": "A2"},
                {"dl_nbr": 1001, "tr_id": "B"},
                {"dl_nbr": 1001, "tr_id": "C"},
            ]
        )

        # Deal 1002 tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1002, "tr_id": "SEN-A"},
                {"dl_nbr": 1002, "tr_id": "SUB-B"},
                {"dl_nbr": 1002, "tr_id": "JUN-C"},
            ]
        )

        # Deal 1003 tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1003, "tr_id": "CLASS-A"},
                {"dl_nbr": 1003, "tr_id": "CLASS-B"},
                {"dl_nbr": 1003, "tr_id": "CLASS-C"},
            ]
        )

        # Deal 1004 tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1004, "tr_id": "A1"},
                {"dl_nbr": 1004, "tr_id": "A2"},
                {"dl_nbr": 1004, "tr_id": "A3"},
                {"dl_nbr": 1004, "tr_id": "B"},
            ]
        )

        # Deal 1005 tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1005, "tr_id": "SENIOR"},
                {"dl_nbr": 1005, "tr_id": "MEZZ"},
                {"dl_nbr": 1005, "tr_id": "JUNIOR"},
            ]
        )

        # Deal 1006 tranches
        tranches_data.extend(
            [
                {"dl_nbr": 1006, "tr_id": "A"},
                {"dl_nbr": 1006, "tr_id": "B"},
                {"dl_nbr": 1006, "tr_id": "C"},
                {"dl_nbr": 1006, "tr_id": "D"},
            ]
        )

        # Create tranches
        created_tranches = []
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)
            created_tranches.append(tranche)

        dw_db.flush()

        # Create sample TrancheBal records
        tranche_bal_data = []
        for tranche in created_tranches:
            # Create a sample tranche record for each tranche with cycle date
            tranche_bal_data.append({
                "dl_nbr": tranche.dl_nbr,
                "tr_id": tranche.tr_id,
                "cycle_date": "2024-03-31",  # Sample cycle date
            })

        # Create tranche balances
        for bal_data in tranche_bal_data:
            tranche_bal = TrancheBal(**bal_data)
            dw_db.add(tranche_bal)

        # Commit all changes
        dw_db.commit()

        print(f"✅ Successfully created sample data:")
        print(f"   📊 {len(created_deals)} deals")
        print(f"   📈 {len(created_tranches)} tranches") 
        print(f"   📊 {len(tranche_bal_data)} tranche balance records")

        # Print deal summary
        print(f"\n📋 Created deals:")
        for deal in created_deals:
            print(f"   Deal {deal.dl_nbr}: {deal.issr_cde}")

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
