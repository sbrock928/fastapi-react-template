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
    from app.calculations.models import Calculation  # noqa: F401 - Updated to use unified model
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
    from app.calculations.models import Calculation  # noqa: F401 - Updated to use unified model
    from app.datawarehouse.models import Deal, Tranche, TrancheBal, DealCdiVarRpt  # noqa: F401 - ADDED DealCdiVarRpt

    print("Dropping config database tables...")
    Base.metadata.drop_all(bind=engine)

    print("Dropping data warehouse tables...")
    DWBase.metadata.drop_all(bind=dw_engine)

    print("All tables dropped!")


# ===== UPDATED CALCULATION SEEDING =====


def create_standard_calculations():
    """Create standard calculation system with unified calculation model."""
    # Import only when needed to avoid circular imports
    from app.calculations.models import (
        Calculation,
        CalculationType,
        AggregationFunction,
        SourceModel,
        GroupLevel,
    )
    from app.calculations.service import UnifiedCalculationService
    from app.calculations.schemas import UserAggregationCalculationCreate, SystemSqlCalculationCreate

    # Create both database sessions
    config_db = SessionLocal()
    dw_db = next(get_dw_db())

    try:
        # Check if calculations already exist
        existing_count = config_db.query(Calculation).count()
        if existing_count > 0:
            print(f"Calculations already exist ({existing_count} found). Skipping creation.")
            return

        print("Creating unified calculation system...")

        # Initialize unified calculation service with both databases - FIXED parameter order
        calc_service = UnifiedCalculationService(config_db, dw_db)

        # ===== 1. USER-DEFINED CALCULATIONS =====
        print("Creating user-defined calculations...")
        
        user_calculations = [
            {
                "name": "Total Ending Balance",
                "description": "Sum of all tranche ending balances",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_end_bal_amt",
                "group_level": GroupLevel.DEAL,
            },
            {
                "name": "Average Pass Through Rate",
                "description": "Weighted average pass through rate",
                "aggregation_function": AggregationFunction.WEIGHTED_AVG,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_pass_thru_rte",
                "weight_field": "tr_end_bal_amt",
                "group_level": GroupLevel.DEAL,
            },
        ]

        user_created_count = 0
        for calc_config in user_calculations:
            try:
                request = UserAggregationCalculationCreate(**calc_config)
                created_calc = calc_service.create_user_aggregation_calculation(request, "system")
                print(f"✅ Created user calculation: {created_calc.name}")
                user_created_count += 1
            except Exception as e:
                print(f"⚠️  Error creating user-defined calculation {calc_config['name']}: {str(e)}")

        print(f"✅ Created {user_created_count} user-defined calculations")

        # ===== 2. SYSTEM SQL CALCULATIONS =====
        print("Creating system SQL calculations...")
        
        system_calculations = [
            {
                "name": "Issuer Type Classification",
                "description": "Classify deals by issuer type",
                "raw_sql": """
                SELECT 
                    d.dl_nbr,
                    CASE 
                        WHEN d.issr_cde LIKE 'BANK%' THEN 'Bank'
                        WHEN d.issr_cde LIKE 'CREDIT%' THEN 'Credit Union'
                        ELSE 'Other'
                    END as issuer_type
                FROM deal d
                """,
                "result_column_name": "issuer_type",
                "group_level": GroupLevel.DEAL,
            },
        ]

        system_created_count = 0
        for calc_config in system_calculations:
            try:
                request = SystemSqlCalculationCreate(**calc_config)
                created_calc = calc_service.create_system_sql_calculation(request, "system")
                print(f"✅ Created system calculation: {created_calc.name}")
                system_created_count += 1
            except Exception as e:
                print(f"⚠️  Error creating system SQL calculation {calc_config['name']}: {str(e)}")

        print(f"✅ Created {system_created_count} system SQL calculations")

        print("\n📋 Final counts:")
        print(f"   User calculations: {user_created_count}")
        print(f"   System calculations: {system_created_count}")
        print(f"   Total calculations: {user_created_count + system_created_count}")

    except Exception as e:
        config_db.rollback()
        print(f"❌ Error in create_standard_calculations: {str(e)}")
        raise
    finally:
        config_db.close()
        dw_db.close()


# ===== SAMPLE DATA CREATION =====


def create_sample_data():
    """Create sample data in the data warehouse - FIXED VERSION."""
    
    # Import models - INCLUDING the new CDI model
    from app.datawarehouse.models import Deal, Tranche, TrancheBal, DealCdiVarRpt
    
    dw_db = next(get_dw_db())
    
    try:
        # Check if data already exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 0:
            print("Sample data already exists. Skipping creation.")
            return

        print("Creating sample data...")

        # Create deals
        deals = [
            Deal(dl_nbr=100, issr_cde="BANK01", cdi_file_nme="DEAL100", CDB_cdi_file_nme="CDB100"),
            Deal(dl_nbr=200, issr_cde="CREDIT01", cdi_file_nme="DEAL200", CDB_cdi_file_nme="CDB200"),
            Deal(dl_nbr=300, issr_cde="OTHER01", cdi_file_nme="DEAL300", CDB_cdi_file_nme="CDB300"),
        ]
        
        dw_db.add_all(deals)
        dw_db.flush()  # Flush to get the IDs

        # Create tranches
        tranches = [
            # Deal 100
            Tranche(dl_nbr=100, tr_id="A", tr_cusip_id="100000AAA0"),
            Tranche(dl_nbr=100, tr_id="B", tr_cusip_id="100000BBB0"),
            
            # Deal 200
            Tranche(dl_nbr=200, tr_id="A", tr_cusip_id="200000AAA0"),
            Tranche(dl_nbr=200, tr_id="B", tr_cusip_id="200000BBB0"),
            
            # Deal 300
            Tranche(dl_nbr=300, tr_id="A", tr_cusip_id="300000AAA0"),
        ]
        
        dw_db.add_all(tranches)
        dw_db.flush()

        # Create tranche balances
        tranche_bals = [
            # Deal 100, Cycle 1
            TrancheBal(
                dl_nbr=100, tr_id="A", cycle_cde=1, 
                tr_end_bal_amt=1000000, tr_prin_rel_ls_amt=50000, tr_pass_thru_rte=0.045,
                tr_accrl_days=30, tr_int_dstrb_amt=3750, tr_prin_dstrb_amt=50000,
                tr_int_accrl_amt=3750, tr_int_shtfl_amt=0
            ),
            TrancheBal(
                dl_nbr=100, tr_id="B", cycle_cde=1,
                tr_end_bal_amt=500000, tr_prin_rel_ls_amt=20000, tr_pass_thru_rte=0.055,
                tr_accrl_days=30, tr_int_dstrb_amt=2292, tr_prin_dstrb_amt=20000,
                tr_int_accrl_amt=2292, tr_int_shtfl_amt=0
            ),
            
            # Deal 200, Cycle 1
            TrancheBal(
                dl_nbr=200, tr_id="A", cycle_cde=1,
                tr_end_bal_amt=2000000, tr_prin_rel_ls_amt=100000, tr_pass_thru_rte=0.040,
                tr_accrl_days=30, tr_int_dstrb_amt=6667, tr_prin_dstrb_amt=100000,
                tr_int_accrl_amt=6667, tr_int_shtfl_amt=0
            ),
            TrancheBal(
                dl_nbr=200, tr_id="B", cycle_cde=1,
                tr_end_bal_amt=800000, tr_prin_rel_ls_amt=50000, tr_pass_thru_rte=0.060,
                tr_accrl_days=30, tr_int_dstrb_amt=4000, tr_prin_dstrb_amt=50000,
                tr_int_accrl_amt=4000, tr_int_shtfl_amt=0
            ),
            
            # Deal 300, Cycle 1
            TrancheBal(
                dl_nbr=300, tr_id="A", cycle_cde=1,
                tr_end_bal_amt=1500000, tr_prin_rel_ls_amt=100000, tr_pass_thru_rte=0.035,
                tr_accrl_days=30, tr_int_dstrb_amt=4375, tr_prin_dstrb_amt=100000,
                tr_int_accrl_amt=4375, tr_int_shtfl_amt=0
            ),
        ]
        
        dw_db.add_all(tranche_bals)
        dw_db.flush()
        
        # Create sample CDI variables
        from sqlalchemy.sql import func
        current_time = func.now()
        cdi_variables = [
            # Investment Income for Deal 100
            DealCdiVarRpt(
                dl_nbr=100, cycle_cde=1,
                dl_cdi_var_nme="#RPT_RRI_A".ljust(32),  # Pad to CHAR(32)
                dl_cdi_var_value="125000.00".ljust(32),  # Pad to CHAR(32)
                lst_upd_dtm=current_time,
                lst_upd_user_id='system',
                lst_upd_host_nme='localhost'
            ),
            DealCdiVarRpt(
                dl_nbr=100, cycle_cde=1,
                dl_cdi_var_nme="#RPT_RRI_B".ljust(32),
                dl_cdi_var_value="65000.00".ljust(32),
                lst_upd_dtm=current_time,
                lst_upd_user_id='system',
                lst_upd_host_nme='localhost'
            ),
            
            # Excess Interest for Deal 200
            DealCdiVarRpt(
                dl_nbr=200, cycle_cde=1,
                dl_cdi_var_nme="#RPT_EXC_A".ljust(32),
                dl_cdi_var_value="25000.00".ljust(32),
                lst_upd_dtm=current_time,
                lst_upd_user_id='system',
                lst_upd_host_nme='localhost'
            ),
        ]
        
        dw_db.add_all(cdi_variables)
        dw_db.commit()
        
        print("✅ Sample data created successfully (including CDI variables)")
        print(f"   Created {len(deals)} deals")
        print(f"   Created {len(tranches)} tranches") 
        print(f"   Created {len(tranche_bals)} tranche balance records")
        print(f"   Created {len(cdi_variables)} CDI variable records")
        
    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating sample data: {str(e)}")
        raise  # Re-raise to see the full error
        
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