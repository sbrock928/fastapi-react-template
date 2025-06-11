# app/core/database.py
"""Enhanced database configuration with dual database support and updated calculation system."""

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
    from app.calculations.models import UserCalculation, SystemCalculation  # noqa: F401
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
    from app.calculations.models import UserCalculation, SystemCalculation  # noqa: F401
    from app.datawarehouse.models import Deal, Tranche, TrancheBal  # noqa: F401

    print("Dropping config database tables...")
    Base.metadata.drop_all(bind=engine)

    print("Dropping data warehouse tables...")
    DWBase.metadata.drop_all(bind=dw_engine)

    print("All tables dropped!")


# ===== UPDATED CALCULATION SEEDING =====


def create_standard_calculations():
    """Create standard calculation system with separated User and System calculations."""
    # Import only when needed to avoid circular imports
    from app.calculations.models import (
        UserCalculation,
        SystemCalculation,
        AggregationFunction,
        SourceModel,
        GroupLevel,
    )
    from app.calculations.service import UserCalculationService, SystemCalculationService
    from app.calculations.schemas import UserCalculationCreate, SystemCalculationCreate

    # Create config database session
    config_db = SessionLocal()

    try:
        # Check if calculations already exist
        existing_user_count = config_db.query(UserCalculation).count()
        existing_system_count = config_db.query(SystemCalculation).count()
        if existing_user_count > 0 or existing_system_count > 0:
            print(f"Calculations already exist ({existing_user_count} user, {existing_system_count} system found). Skipping creation.")
            return

        print("Creating separated calculation system...")

        # Initialize calculation services
        user_calc_service = UserCalculationService(config_db)
        system_calc_service = SystemCalculationService(config_db)

        # ===== 1. CREATE USER DEFINED CALCULATIONS =====
        print("Creating user-defined calculations...")

        user_defined_calcs = [
            {
                "name": "Total Ending Balance",
                "description": "Sum of all tranche ending balance amounts",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_end_bal_amt",
                "group_level": GroupLevel.DEAL,
            },
            {
                "name": "Average Pass Through Rate",
                "description": "Weighted average pass through rate across tranches",
                "aggregation_function": AggregationFunction.WEIGHTED_AVG,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_pass_thru_rte",
                "weight_field": "tr_end_bal_amt",
                "group_level": GroupLevel.DEAL,
            },
        ]

        user_defined_count = 0
        for calc_data in user_defined_calcs:
            try:
                request = UserCalculationCreate(**calc_data)
                user_calc_service.create_user_calculation(request, "system_initializer")
                user_defined_count += 1
            except Exception as e:
                print(f"⚠️  Error creating user-defined calculation {calc_data['name']}: {e}")

        print(f"✅ Created {user_defined_count} user-defined calculations")

        # ===== 2. CREATE SYSTEM SQL CALCULATIONS =====
        print("Creating system SQL calculations...")

        system_sql_calcs = [
            {
                "name": "Issuer Type Classification",
                "description": "Categorizes deals by issuer type (GSE, Government, Private)",
                "group_level": GroupLevel.DEAL,
                "raw_sql": """
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
                        WHEN deal.issr_cde LIKE '%FNMA%' THEN 'GSE'
                        WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
                        ELSE 'Private'
                    END AS issuer_type
                FROM deal
                """,
                "result_column_name": "issuer_type",
            },
        ]

        system_sql_count = 0
        for calc_data in system_sql_calcs:
            try:
                request = SystemCalculationCreate(**calc_data)
                created_calc = system_calc_service.create_system_calculation(request, "system_initializer")
                # Auto-approve system calculations created during initialization
                system_calc_service.approve_system_calculation(created_calc.id, "system_initializer")
                system_sql_count += 1
            except Exception as e:
                print(f"⚠️  Error creating system SQL calculation {calc_data['name']}: {e}")

        print(f"✅ Created {system_sql_count} system SQL calculations")

        # Print final counts
        config_db.commit()
        final_user_count = config_db.query(UserCalculation).filter(UserCalculation.is_active == True).count()
        final_system_count = config_db.query(SystemCalculation).filter(SystemCalculation.is_active == True).count()
        print(f"\n📋 Final counts:")
        print(f"   User calculations: {final_user_count}")
        print(f"   System calculations: {final_system_count}")

    except Exception as e:
        config_db.rollback()
        print(f"❌ Error creating calculation system: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        config_db.close()


# ===== SAMPLE DATA CREATION =====


def create_sample_data():
    """Create simple sample data for development and testing."""
    from app.datawarehouse.models import Deal, Tranche, TrancheBal
    import random

    # Create data warehouse session
    dw_db = DWSessionLocal()

    try:
        # Check if sample data already exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 0:
            print(f"Sample data already exists ({existing_deals} deals found). Skipping creation.")
            return

        print("Creating simple sample data...")

        # Create 5 simple deals
        deals_data = [
            {"dl_nbr": 1001, "issr_cde": "FHLMC24", "cdi_file_nme": "FH1001_CDI"},
            {"dl_nbr": 1002, "issr_cde": "FNMA24", "cdi_file_nme": "FN1002_CDI"},
            {"dl_nbr": 1003, "issr_cde": "GNMA24", "cdi_file_nme": "GN1003_CDI"},
            {"dl_nbr": 1004, "issr_cde": "FHLMC24", "cdi_file_nme": "FH1004_CDI"},
            {"dl_nbr": 1005, "issr_cde": "FNMA24", "cdi_file_nme": "FN1005_CDI"},
        ]

        # Create deals
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)

        # Create simple tranches (A, B, C for each deal)
        for deal_data in deals_data:
            for tr_id in ["A", "B", "C"]:
                tranche = Tranche(
                    dl_nbr=deal_data["dl_nbr"],
                    tr_id=tr_id,
                    tr_cusip_id=f"{deal_data['issr_cde'][:4]}{tr_id}{str(deal_data['dl_nbr'])[-3:]}"
                )
                dw_db.add(tranche)

                # Create balance data for cycle 202404
                balance = TrancheBal(
                    dl_nbr=deal_data["dl_nbr"],
                    tr_id=tr_id,
                    cycle_cde=202404,
                    tr_end_bal_amt=random.uniform(1000000, 50000000),
                    tr_prin_rel_ls_amt=random.uniform(10000, 500000),  # Added this
                    tr_pass_thru_rte=random.uniform(0.02, 0.08),
                    tr_accrl_days=random.randint(28, 31),  # Added this
                    tr_int_dstrb_amt=random.uniform(5000, 100000),
                    tr_prin_dstrb_amt=random.uniform(50000, 1000000),
                    tr_int_accrl_amt=random.uniform(1000, 50000),  # Added this
                    tr_int_shtfl_amt=random.uniform(0, 10000),  # Added this
                )
                dw_db.add(balance)

        dw_db.commit()
        print(f"✅ Created 5 deals with 15 tranches and balance data")

    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating sample data: {e}")
        raise
    finally:
        dw_db.close()


# ===== INITIALIZATION FUNCTION =====


def initialize_databases(force_recreate: bool = False):
    """Initialize both databases with tables, calculations, and sample data."""
    print("Initializing dual database system with separated calculation support...")

    if force_recreate:
        print("🔄 Force recreate mode: Dropping existing tables...")
        drop_all_tables()

    # Create all tables
    create_all_tables()

    # Create separated calculation system (must come before sample data)
    create_standard_calculations()

    # Create sample data for development
    create_sample_data()

    print("Enhanced database initialization complete! 🎉")


if __name__ == "__main__":
    # Allow running this file directly to initialize databases
    initialize_databases()