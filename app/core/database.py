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
    from app.calculations.models import Calculation  # noqa: F401
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
    from app.calculations.models import Calculation  # noqa: F401
    from app.datawarehouse.models import Deal, Tranche, TrancheBal  # noqa: F401

    print("Dropping config database tables...")
    Base.metadata.drop_all(bind=engine)

    print("Dropping data warehouse tables...")
    DWBase.metadata.drop_all(bind=dw_engine)

    print("All tables dropped!")


# ===== UPDATED CALCULATION SEEDING =====


def create_standard_calculations():
    """Create standard calculation system with User Defined, System Field, and System SQL types."""
    from app.calculations.models import Calculation, CalculationType, AggregationFunction, SourceModel, GroupLevel
    from app.calculations.service import CalculationService
    from app.calculations.schemas import UserDefinedCalculationCreate, SystemFieldCalculationCreate, SystemSQLCalculationCreate
    
    # Create config database session
    config_db = SessionLocal()
    
    try:
        # Check if calculations already exist
        existing_count = config_db.query(Calculation).count()
        if existing_count > 0:
            print(f"Calculations already exist ({existing_count} found). Skipping creation.")
            return
        
        print("Creating enhanced calculation system...")
        
        # Initialize calculation service
        calc_service = CalculationService(config_db)
        
        # ===== 1. AUTO-GENERATE SYSTEM FIELD CALCULATIONS =====
        print("Auto-generating system field calculations from model introspection...")
        auto_gen_result = calc_service.auto_generate_system_fields()
        print(f"✅ Auto-generated {auto_gen_result['generated_count']} system field calculations")
        if auto_gen_result['errors']:
            print(f"⚠️  Errors during auto-generation: {auto_gen_result['errors']}")
        
        # ===== 2. CREATE SAMPLE USER DEFINED CALCULATIONS =====
        print("Creating sample user-defined calculations...")
        
        user_defined_calcs = [
            {
                "name": "Total Ending Balance",
                "description": "Sum of all tranche ending balance amounts",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_end_bal_amt",
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "Average Pass Through Rate",
                "description": "Weighted average pass through rate across tranches",
                "aggregation_function": AggregationFunction.WEIGHTED_AVG,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_pass_thru_rte",
                "weight_field": "tr_end_bal_amt",
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "Total Interest Distribution",
                "description": "Sum of all tranche interest distributions",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_int_dstrb_amt", 
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "Total Principal Distribution",
                "description": "Sum of all tranche principal distributions",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_prin_dstrb_amt",
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "Tranche Count",
                "description": "Count of tranches per deal",
                "aggregation_function": AggregationFunction.COUNT,
                "source_model": SourceModel.TRANCHE,
                "source_field": "tr_id",
                "group_level": GroupLevel.DEAL
            },
            # Tranche-level calculations
            {
                "name": "Ending Balance Amount",
                "description": "Outstanding principal balance at period end (tranche level)",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_end_bal_amt",
                "group_level": GroupLevel.TRANCHE
            },
            {
                "name": "Pass Through Rate",
                "description": "Interest rate passed through to investors (tranche level)", 
                "aggregation_function": AggregationFunction.AVG,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_pass_thru_rte",
                "group_level": GroupLevel.TRANCHE
            },
        ]
        
        user_defined_count = 0
        for calc_data in user_defined_calcs:
            try:
                request = UserDefinedCalculationCreate(**calc_data)
                calc_service.create_user_defined_calculation(request, "system_initializer")
                user_defined_count += 1
            except Exception as e:
                print(f"⚠️  Error creating user-defined calculation {calc_data['name']}: {e}")
        
        print(f"✅ Created {user_defined_count} user-defined calculations")
        
        # ===== 3. CREATE SAMPLE SYSTEM SQL CALCULATIONS =====
        print("Creating sample system SQL calculations...")
        
        system_sql_calcs = [
            {
                "name": "Issuer Type Classification",
                "description": "Categorizes deals by issuer type (GSE, Government, Private)",
                "group_level": GroupLevel.DEAL,
                "raw_sql": """
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN deal.issr_cde LIKE '%FHLMC%' OR deal.issr_cde LIKE '%FNMA%' THEN 'GSE'
                        WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
                        ELSE 'Private'
                    END AS issuer_type
                FROM deal
                """,
                "result_column_name": "issuer_type"
            },
            {
                "name": "Deal Performance Category",
                "description": "Performance categorization based on average pass through rate",
                "group_level": GroupLevel.DEAL,
                "raw_sql": """
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN AVG(tranchebal.tr_pass_thru_rte) >= 0.06 THEN 'High Rate'
                        WHEN AVG(tranchebal.tr_pass_thru_rte) >= 0.04 THEN 'Medium Rate'
                        ELSE 'Low Rate'
                    END AS performance_category
                FROM deal
                JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
                JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id
                GROUP BY deal.dl_nbr
                """,
                "result_column_name": "performance_category"
            },
            {
                "name": "Tranche Size Category",
                "description": "Size categorization of individual tranches",
                "group_level": GroupLevel.TRANCHE,
                "raw_sql": """
                SELECT 
                    deal.dl_nbr,
                    tranche.tr_id,
                    CASE 
                        WHEN tranchebal.tr_end_bal_amt >= 25000000 THEN 'Large'
                        WHEN tranchebal.tr_end_bal_amt >= 10000000 THEN 'Medium'
                        ELSE 'Small'
                    END AS size_category
                FROM deal
                JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
                JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id
                """,
                "result_column_name": "size_category"
            }
        ]
        
        system_sql_count = 0
        for calc_data in system_sql_calcs:
            try:
                request = SystemSQLCalculationCreate(**calc_data)
                calc_service.create_system_sql_calculation(request, "system_initializer")
                system_sql_count += 1
            except Exception as e:
                print(f"⚠️  Error creating system SQL calculation {calc_data['name']}: {e}")
        
        print(f"✅ Created {system_sql_count} system SQL calculations")
        
        # ===== SUMMARY =====
        total_calculations = auto_gen_result['generated_count'] + user_defined_count + system_sql_count
        print(f"\n🎉 Successfully created enhanced calculation system:")
        print(f"   📊 {auto_gen_result['generated_count']} system field calculations (auto-generated)")
        print(f"   👤 {user_defined_count} user-defined calculations")
        print(f"   🔧 {system_sql_count} system SQL calculations")
        print(f"   📈 {total_calculations} total calculations")
        
        # Print breakdown by type
        config_db.commit()  # Commit changes before querying counts
        from app.calculations.dao import CalculationDAO
        dao = CalculationDAO(config_db)
        counts = dao.count_by_type()
        print(f"\n📋 Final counts by type:")
        for calc_type, count in counts.items():
            print(f"   {calc_type}: {count}")
        
    except Exception as e:
        config_db.rollback()
        print(f"❌ Error creating enhanced calculation system: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        config_db.close()


# ===== SAMPLE DATA CREATION (unchanged) =====


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

        print("Creating comprehensive sample data with issuer-based structure...")

        # Define 3 main issuers with multiple deals each, plus some high-tranche deals
        issuers_config = [
            {
                "issuer_code": "FHLMC24",
                "deal_count": 8,
                "deal_prefix": "FH"
            },
            {
                "issuer_code": "FNMA24", 
                "deal_count": 7,
                "deal_prefix": "FN"
            },
            {
                "issuer_code": "GNMA24",
                "deal_count": 5,
                "deal_prefix": "GN"
            },
            # Add issuers with high-tranche deals for UI testing
            {
                "issuer_code": "COMPLEX24",
                "deal_count": 3,
                "deal_prefix": "CX"
            }
        ]

        # Create deals for each issuer
        deals_data = []
        deal_counter = 1001
        
        for issuer in issuers_config:
            for i in range(issuer["deal_count"]):
                deal_data = {
                    "dl_nbr": deal_counter,
                    "issr_cde": issuer["issuer_code"],
                    "cdi_file_nme": f"{issuer['deal_prefix']}{deal_counter:04d}_CDI",
                    "CDB_cdi_file_nme": f"{issuer['deal_prefix']}{deal_counter:04d}_CDB" if i % 3 == 0 else None,  # About 1/3 have CDB files
                }
                deals_data.append(deal_data)
                deal_counter += 1

        # Create deals
        created_deals = []
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
            created_deals.append(deal)

        dw_db.flush()  # Flush to get IDs but don't commit yet

        # Generate tranches for all deals with varied patterns by issuer
        print("Generating tranches for all deals...")
        tranches_data = []
        
        # Different tranche patterns for different issuers
        issuer_tranche_patterns = {
            "FHLMC24": [
                ["A1", "A2", "B"],
                ["SEN", "SUB", "JUN"],
                ["CLASS-A", "CLASS-B", "CLASS-C"],
                ["A", "B", "C"]
            ],
            "FNMA24": [
                ["SENIOR", "MEZZ", "JUNIOR"],
                ["A1", "A2", "A3", "B"],
                ["PASS", "IO", "PO"],
                ["X", "Y", "Z"]
            ],
            "GNMA24": [
                ["A", "B"],
                ["I", "II", "III"],
                ["FLOAT", "FIXED"],
                ["1A", "1B", "2"]
            ],
            # Complex deals with many tranches for UI testing
            "COMPLEX24": [
                # First deal: 35 tranches with sequential pattern
                [f"A{i:02d}" for i in range(1, 36)],
                # Second deal: 42 tranches with mixed classes
                [f"CLASS-{chr(65 + i//10)}{i%10 + 1}" for i in range(42)],
                # Third deal: 38 tranches with varied naming
                ([f"SENIOR-{i}" for i in range(1, 11)] + 
                 [f"MEZZ-{i}" for i in range(1, 16)] + 
                 [f"JUNIOR-{i}" for i in range(1, 14)])
            ]
        }
        
        for deal in created_deals:
            # Get patterns for this issuer
            patterns = issuer_tranche_patterns[deal.issr_cde]
            
            # For COMPLEX24 deals, use specific high-tranche patterns
            if deal.issr_cde == "COMPLEX24":
                # Get the index of this deal within the COMPLEX24 deals
                complex_deals = [d for d in created_deals if d.issr_cde == "COMPLEX24"]
                deal_index = complex_deals.index(deal)
                pattern = patterns[deal_index % len(patterns)]
            else:
                pattern = random.choice(patterns)
            
            for tr_id in pattern:
                tranche_data = {
                    "dl_nbr": deal.dl_nbr,
                    "tr_id": tr_id,
                    "tr_cusip_id": f"{deal.issr_cde[:6]}{tr_id[:3]}{str(deal.dl_nbr)[-3:]}"  # Generate synthetic CUSIP
                }
                tranches_data.append(tranche_data)

        # Create all tranches
        created_tranches = []
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)
            created_tranches.append(tranche)

        dw_db.flush()

        # Generate tranche balance records
        print("Generating tranche balance data...")
        
        base_cycles = [202401, 202402, 202403, 202404]  # Different cycle codes
        tranche_bal_data = []
        for tranche in created_tranches:
            # Create 1-3 balance records per tranche with different cycle codes
            num_records = random.randint(1, 3)
            
            for record_num in range(num_records):
                bal_data = {
                    "dl_nbr": tranche.dl_nbr,
                    "tr_id": tranche.tr_id,
                    "cycle_cde": base_cycles[record_num % len(base_cycles)],
                    # Generate realistic financial data
                    "tr_end_bal_amt": round(random.uniform(1000000, 50000000), 2),
                    "tr_prin_rel_ls_amt": round(random.uniform(10000, 500000), 2),
                    "tr_pass_thru_rte": round(random.uniform(0.02, 0.08), 4),
                    "tr_accrl_days": random.randint(28, 31),
                    "tr_int_dstrb_amt": round(random.uniform(5000, 100000), 2),
                    "tr_prin_dstrb_amt": round(random.uniform(50000, 1000000), 2),
                    "tr_int_accrl_amt": round(random.uniform(1000, 50000), 2),
                    "tr_int_shtfl_amt": round(random.uniform(0, 10000), 2),
                }
                tranche_bal_data.append(bal_data)

        # Create tranche balance records
        for bal_data in tranche_bal_data:
            tranche_bal = TrancheBal(**bal_data)
            dw_db.add(tranche_bal)

        # Commit everything
        print("Committing all data to database...")
        dw_db.commit()

        print(f"✅ Successfully created issuer-based sample data:")
        print(f"   📊 {len(created_deals)} deals across 4 issuers")
        print(f"   📈 {len(created_tranches)} tranches")
        print(f"   📊 {len(tranche_bal_data)} tranche balance records")

        # Print summary by issuer
        print(f"\n📋 Deals by issuer:")
        for issuer in issuers_config:
            issuer_deals = [d for d in created_deals if d.issr_cde == issuer["issuer_code"]]
            issuer_tranches = [t for t in created_tranches if any(d.dl_nbr == t.dl_nbr for d in issuer_deals)]
            print(f"   {issuer['issuer_code']}: {len(issuer_deals)} deals, {len(issuer_tranches)} tranches")

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
    """Initialize both databases with tables, calculations, and sample data."""
    print("Initializing dual database system with enhanced calculation support...")

    if force_recreate:
        print("🔄 Force recreate mode: Dropping existing tables...")
        drop_all_tables()

    # Create all tables
    create_all_tables()

    # Create enhanced calculation system (must come before sample data)
    create_standard_calculations()

    # Create sample data for development
    create_sample_data()

    print("Enhanced database initialization complete! 🎉")


if __name__ == "__main__":
    # Allow running this file directly to initialize databases
    initialize_databases()