# app/core/database.py
"""Enhanced database configuration with dual database support and audit/execution logging."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# ===== CONFIG DATABASE (existing) =====
# Stores report configurations, users, employees, etc.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vibez_config.db")

# Enhanced SQLite configuration for better concurrency
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    sqlite_connect_args = {
        "check_same_thread": False,
        "timeout": 30,  # 30 second timeout for database locks
    }
    
    # For SQLite, we use a smaller pool since it doesn't handle many concurrent writers well
    engine = create_engine(
        DATABASE_URL,
        connect_args=sqlite_connect_args,
        pool_size=2,  # Small pool for SQLite
        max_overflow=3,  # Limited overflow
        pool_timeout=30,  # Connection timeout
        pool_recycle=3600,  # Recycle connections every hour
        pool_pre_ping=True,  # Verify connections before use
    )
else:
    # Production database (T-SQL) configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,  # Larger pool for production databases
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

# Enable WAL mode for SQLite to improve concurrency
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance and concurrency."""
        cursor = dbapi_connection.cursor()
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Set reasonable timeout
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ===== DATA WAREHOUSE DATABASE (new) =====
# Stores financial data: deals, tranches, etc.
DATA_WAREHOUSE_URL = os.getenv("DATA_WAREHOUSE_URL", "sqlite:///./vibez_datawarehouse.db")

# Enhanced configuration for data warehouse
if DATA_WAREHOUSE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    dw_sqlite_connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }
    
    dw_engine = create_engine(
        DATA_WAREHOUSE_URL,
        connect_args=dw_sqlite_connect_args,
        pool_size=2,
        max_overflow=3,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
else:
    # Production database configuration
    dw_engine = create_engine(
        DATA_WAREHOUSE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

# Enable WAL mode for data warehouse SQLite too
if DATA_WAREHOUSE_URL.startswith("sqlite"):
    @event.listens_for(dw_engine, "connect")
    def set_dw_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for data warehouse."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
    from app.calculations.audit_models import CalculationAuditLog  # noqa: F401 - NEW (Optimized version)
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
    from app.calculations.audit_models import CalculationAuditLog  # noqa: F401 - NEW (Optimized version)
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
    from app.calculations.dao import UserCalculationDAO, SystemCalculationDAO
    from app.calculations.audit_models import audit_context  # NEW - Import audit context

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

        # Initialize calculation services with DAOs
        user_calc_dao = UserCalculationDAO(config_db)
        system_calc_dao = SystemCalculationDAO(config_db)
        user_calc_service = UserCalculationService(user_calc_dao)
        system_calc_service = SystemCalculationService(system_calc_dao)

        # ===== 1. CREATE USER DEFINED CALCULATIONS =====
        print("Creating user-defined calculations...")

        # Use audit context for system initialization
        with audit_context("system_initializer"):
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
    """Create simple sample data for development and testing with temporary FK disable."""
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

        # Temporarily disable foreign key constraints for sample data creation
        print("  Temporarily disabling foreign key constraints...")
        dw_db.execute("PRAGMA foreign_keys=OFF")

        # Create 5 simple deals
        deals_data = [
            {"dl_nbr": 1001, "issr_cde": "FHLMC24", "cdi_file_nme": "FH1001_CDI"},
            {"dl_nbr": 1002, "issr_cde": "FNMA24", "cdi_file_nme": "FN1002_CDI"},
            {"dl_nbr": 1003, "issr_cde": "GNMA24", "cdi_file_nme": "GN1003_CDI"},
            {"dl_nbr": 1004, "issr_cde": "FHLMC24", "cdi_file_nme": "FH1004_CDI"},
            {"dl_nbr": 1005, "issr_cde": "FNMA24", "cdi_file_nme": "FN1005_CDI"},
        ]

        # Create deals
        print("  Creating deals...")
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
        print(f"  ✅ Added {len(deals_data)} deals to session")

        # Create tranches
        print("  Creating tranches...")
        tranches_created = 0
        for deal_data in deals_data:
            for tr_id in ["A", "B", "C"]:
                tranche = Tranche(
                    dl_nbr=deal_data["dl_nbr"],
                    tr_id=tr_id,
                    tr_cusip_id=f"{deal_data['issr_cde'][:4]}{tr_id}{str(deal_data['dl_nbr'])[-3:]}"
                )
                dw_db.add(tranche)
                tranches_created += 1
        print(f"  ✅ Added {tranches_created} tranches to session")

        # Create tranche balances
        print("  Creating tranche balances...")
        balances_created = 0
        for deal_data in deals_data:
            for tr_id in ["A", "B", "C"]:
                balance = TrancheBal(
                    dl_nbr=deal_data["dl_nbr"],
                    tr_id=tr_id,
                    cycle_cde=202404,
                    tr_end_bal_amt=random.uniform(1000000, 50000000),
                    tr_prin_rel_ls_amt=random.uniform(10000, 500000),
                    tr_pass_thru_rte=random.uniform(0.02, 0.08),
                    tr_accrl_days=random.randint(28, 31),
                    tr_int_dstrb_amt=random.uniform(5000, 100000),
                    tr_prin_dstrb_amt=random.uniform(50000, 1000000),
                    tr_int_accrl_amt=random.uniform(1000, 50000),
                    tr_int_shtfl_amt=random.uniform(0, 10000),
                )
                dw_db.add(balance)
                balances_created += 1
        print(f"  ✅ Added {balances_created} tranche balances to session")

        # Commit all data with FK constraints disabled
        print("  Committing all sample data...")
        dw_db.commit()

        # Re-enable foreign key constraints
        print("  Re-enabling foreign key constraints...")
        dw_db.execute("PRAGMA foreign_keys=ON")
        dw_db.commit()

        print(f"✅ Sample data creation complete: {len(deals_data)} deals, {tranches_created} tranches, {balances_created} balances")

        # Verify data integrity after re-enabling constraints
        print("  Verifying data integrity...")
        deals_count = dw_db.query(Deal).count()
        tranches_count = dw_db.query(Tranche).count()
        balances_count = dw_db.query(TrancheBal).count()
        print(f"  📊 Final counts: {deals_count} deals, {tranches_count} tranches, {balances_count} balances")

    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating sample data: {e}")
        print("  Attempting to re-enable foreign key constraints...")
        try:
            dw_db.execute("PRAGMA foreign_keys=ON")
            dw_db.commit()
        except:
            pass
        raise
    finally:
        dw_db.close()


# ===== INITIALIZATION FUNCTION =====


def initialize_databases(force_recreate: bool = False):
    """Initialize both databases with tables, calculations, and sample data."""
    print("Initializing dual database system with optimized connection management...")

    if force_recreate:
        print("🔄 Force recreate mode: Dropping existing tables...")
        drop_all_tables()

    # Create all tables (including new audit and execution log tables)
    create_all_tables()

    # Initialize audit event listeners (happens automatically when importing audit_models)
    print("🔍 Initializing optimized calculation audit system...")
    try:
        from app.calculations.audit_models import setup_calculation_audit_listeners
        # Event listeners are already set up when the module is imported
        print("✅ Calculation audit system initialized with singleton logger and connection pooling")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize audit system: {e}")

    # Create separated calculation system (must come before sample data)
    create_standard_calculations()

    # Create sample data for development
    create_sample_data()

    print("Enhanced database initialization complete! 🎉")
    print("📊 New features:")
    print("   • Report execution logging")
    print("   • Optimized calculation audit trail with connection pooling")
    print("   • Enhanced SQLite concurrency with WAL mode")
    print("   • Singleton audit logger for efficient resource usage")
    print("   • Enhanced reporting services")


if __name__ == "__main__":
    # Allow running this file directly to initialize databases
    initialize_databases()