"""Enhanced database configuration with dual database support."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# ===== CONFIG DATABASE (existing) =====
# Stores report configurations, users, employees, etc.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vibez_config.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ===== DATA WAREHOUSE DATABASE (new) =====
# Stores financial data: deals, tranches, etc.
DATA_WAREHOUSE_URL = os.getenv("DATA_WAREHOUSE_URL", "sqlite:///./vibez_datawarehouse.db")

dw_engine = create_engine(
    DATA_WAREHOUSE_URL,
    connect_args={"check_same_thread": False} if DATA_WAREHOUSE_URL.startswith("sqlite") else {},
)
DWSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=dw_engine)
DWBase = declarative_base()


# ===== SESSION GENERATORS =====


def get_db():
    """Get config database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_dw_db():
    """Get data warehouse database session."""
    db = DWSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - for backward compatibility."""
    try:
        initialize_databases()
    except Exception as e:
        if "has no column named" in str(e) or "no such column" in str(e):
            print("🔄 Schema mismatch detected. Recreating database with new schema...")
            initialize_databases(force_recreate=True)
        else:
            raise


# ===== TABLE CREATION =====


def create_all_tables():
    """Create tables in both databases."""
    # Import models to ensure they're registered with Base classes
    from app.reporting.models import Report  # noqa: F401
    from app.datawarehouse.models import Deal, Tranche, TrancheBal  # noqa: F401

    print("Creating config database tables...")
    Base.metadata.create_all(bind=engine)

    print("Creating data warehouse tables...")
    DWBase.metadata.create_all(bind=dw_engine)

    print("All tables created successfully!")


def drop_all_tables():
    """Drop all tables in both databases (use with caution!)."""
    # Import models to ensure they're registered with Base classes
    from app.reporting.models import Report  # noqa: F401
    from app.datawarehouse.models import Deal, Tranche  # noqa: F401

    print("Dropping config database tables...")
    Base.metadata.drop_all(bind=engine)

    print("Dropping data warehouse tables...")
    DWBase.metadata.drop_all(bind=dw_engine)

    print("All tables dropped!")


# ===== SAMPLE DATA CREATION =====


def create_sample_data():
    """Create comprehensive sample data for development and testing."""
    from app.datawarehouse.models import Deal, Tranche, TrancheBal
    from datetime import date, timedelta
    from decimal import Decimal
    import random

    # Create data warehouse session
    dw_db = DWSessionLocal()

    try:
        # Check if sample data already exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 0:
            print(f"Sample data already exists ({existing_deals} deals found). Skipping creation.")
            return

        print("Creating comprehensive sample data with new schema...")

        # Sample deals using new schema structure
        deals_data = []
        
        # Create 20 sample deals with realistic issuer codes
        for i in range(1, 21):
            deal_data = {
                "dl_nbr": 1000 + i,
                "issr_cde": f"ISSUER{i:02d}24",
                "cdi_file_nme": f"DL{i:02d}24A",
                "CDB_cdi_file_nme": f"DL{i:02d}24CDB" if i % 3 == 0 else None,  # Not all deals have CDB files
            }
            deals_data.append(deal_data)

        # Create deals
        created_deals = []
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
            created_deals.append(deal)

        dw_db.flush()  # Flush to get IDs but don't commit yet

        # Generate tranches for all deals
        print("Generating tranches for all deals...")
        tranches_data = []
        
        tranche_patterns = [
            ["A1", "A2", "B", "C"],
            ["SENIOR", "MEZZ", "JUNIOR"],
            ["A", "B", "C"],
            ["CLASS-A", "CLASS-B"],
            ["A1", "A2", "A3", "B", "C"],
            ["SEN", "SUB", "JUN"],
        ]
        
        for deal in created_deals:
            # Choose a random tranche pattern
            pattern = random.choice(tranche_patterns)
            
            for idx, tr_id in enumerate(pattern):
                # Generate realistic CUSIP ID (9 characters: 6 issuer + 2 issue + 1 check digit)
                cusip_base = f"{deal.issr_cde[:6]}{idx+1:02d}"
                # Simple check digit calculation (not real CUSIP algorithm but realistic format)
                check_digit = sum(ord(c) for c in cusip_base) % 10
                cusip_id = f"{cusip_base}{check_digit}"
                
                tranche_data = {
                    "dl_nbr": deal.dl_nbr,
                    "tr_id": tr_id,
                    "tr_cusip_id": cusip_id,
                }
                tranches_data.append(tranche_data)

        # Create all tranches
        created_tranches = []
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)
            created_tranches.append(tranche)

        dw_db.flush()        # Generate tranche balance records
        print("Generating tranche balance data...")
        
        cycle_codes = [20241, 20242, 20243]  # Q1, Q2, Q3 2024 as integers
        tranche_bal_data = []
        for tranche in created_tranches:
            # Create 1-3 balance records per tranche with different cycle codes
            num_records = random.randint(1, 3)
            
            for record_num in range(num_records):
                # Generate realistic financial amounts
                end_balance = round(random.uniform(100000, 5000000), 2)
                principal_release = round(random.uniform(1000, 50000), 2)
                interest_distrib = round(random.uniform(500, 10000), 2)
                principal_distrib = round(random.uniform(2000, 25000), 2)
                
                bal_data = {
                    "dl_nbr": tranche.dl_nbr,
                    "tr_id": tranche.tr_id,
                    "cycle_cde": cycle_codes[record_num % len(cycle_codes)],  # Use integer cycle codes
                    # New required fields with realistic financial data
                    "tr_end_bal_amt": end_balance,
                    "tr_prin_rel_ls_amt": principal_release,
                    "tr_pass_thru_rte": round(random.uniform(0.02, 0.08), 4),  # 2-8% rate
                    "tr_accrl_days": random.randint(28, 31),  # Days in month
                    "tr_int_dstrb_amt": interest_distrib,
                    "tr_prin_dstrb_amt": principal_distrib,
                    "tr_int_accrl_amt": round(random.uniform(500, 8000), 2),
                    "tr_int_shtfl_amt": round(random.uniform(0, 1000), 2),  # Shortfall (usually small)
                }
                tranche_bal_data.append(bal_data)

        # Create tranche balance records
        for bal_data in tranche_bal_data:
            tranche_bal = TrancheBal(**bal_data)
            dw_db.add(tranche_bal)

        # Commit everything
        print("Committing all data to database...")
        dw_db.commit()

        print(f"✅ Successfully created sample data with new schema:")
        print(f"   📊 {len(created_deals)} deals")
        print(f"   📈 {len(created_tranches)} tranches")
        print(f"   📊 {len(tranche_bal_data)} tranche balance records")

        # Print summary by deal number range
        print(f"\n📋 Deal number range: {min(d.dl_nbr for d in created_deals)} - {max(d.dl_nbr for d in created_deals)}")
        
        # Print sample of created deals
        print(f"\n📋 Sample deals created:")
        for deal in created_deals[:5]:
            deal_tranches = [t for t in created_tranches if t.dl_nbr == deal.dl_nbr]
            print(f"   Deal {deal.dl_nbr} ({deal.issr_cde}): {len(deal_tranches)} tranches")

        # Print tranche summary
        print(f"\n📈 Tranche ID patterns used:")
        tranche_ids = set(t.tr_id for t in created_tranches)
        print(f"   {', '.join(sorted(tranche_ids))}")

    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        dw_db.close()


# ===== INITIALIZATION FUNCTION =====


def initialize_databases(force_recreate: bool = False):
    """Initialize both databases with tables and sample data."""
    print("Initializing dual database system...")

    if force_recreate:
        print("🔄 Force recreate mode: Dropping existing tables...")
        drop_all_tables()

    # Create all tables
    create_all_tables()

    # Create sample data for development
    create_sample_data()

    print("Database initialization complete!")


if __name__ == "__main__":
    # Allow running this file directly to initialize databases
    initialize_databases()
