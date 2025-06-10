"""Enhanced database configuration with dual database support and calculation seeding."""

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
    from app.datawarehouse.models import Deal, Tranche  # noqa: F401

    print("Dropping config database tables...")
    Base.metadata.drop_all(bind=engine)

    print("Dropping data warehouse tables...")
    DWBase.metadata.drop_all(bind=dw_engine)

    print("All tables dropped!")


# ===== CALCULATION SEEDING =====


def create_standard_calculations():
    """Create standard RAW field and common aggregated calculations."""
    from app.calculations.models import Calculation, AggregationFunction, SourceModel, GroupLevel
    
    # Create config database session
    config_db = SessionLocal()
    
    try:
        # Check if calculations already exist
        existing_count = config_db.query(Calculation).count()
        if existing_count > 0:
            print(f"Standard calculations already exist ({existing_count} found). Skipping creation.")
            return
        
        print("Creating standard calculations...")
        
        # ===== RAW FIELD CALCULATIONS =====
        
        # Deal-level RAW fields (available for both DEAL and TRANCHE scope reports)
        deal_raw_fields = [
            {
                "name": "Deal Number",
                "description": "Unique deal identifier",
                "source_model": SourceModel.DEAL,
                "source_field": "dl_nbr",
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "Issuer Code", 
                "description": "Deal issuer code",
                "source_model": SourceModel.DEAL,
                "source_field": "issr_cde",
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "CDI File Name",
                "description": "CDI file name", 
                "source_model": SourceModel.DEAL,
                "source_field": "cdi_file_nme",
                "group_level": GroupLevel.DEAL
            },
            {
                "name": "CDB CDI File Name",
                "description": "CDB CDI file name",
                "source_model": SourceModel.DEAL, 
                "source_field": "CDB_cdi_file_nme",
                "group_level": GroupLevel.DEAL
            }
        ]
        
        # Tranche-level RAW fields (only available for TRANCHE scope reports)
        tranche_raw_fields = [
            {
                "name": "Tranche ID",
                "description": "Tranche identifier within the deal",
                "source_model": SourceModel.TRANCHE,
                "source_field": "tr_id", 
                "group_level": GroupLevel.TRANCHE
            },
            {
                "name": "Tranche CUSIP ID",
                "description": "CUSIP identifier for the tranche",
                "source_model": SourceModel.TRANCHE,
                "source_field": "tr_cusip_id",
                "group_level": GroupLevel.TRANCHE
            }
        ]
        
        # ===== COMMON AGGREGATED CALCULATIONS =====
        
        # Deal-level aggregated calculations
        deal_aggregated = [
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
            }
        ]
        
        # Tranche-level aggregated calculations (these don't aggregate, but provide TrancheBal data)
        tranche_aggregated = [
            {
                "name": "Ending Balance Amount",
                "description": "Outstanding principal balance at period end",
                "aggregation_function": AggregationFunction.SUM,  # Will be 1 record per tranche
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_end_bal_amt",
                "group_level": GroupLevel.TRANCHE
            },
            {
                "name": "Pass Through Rate",
                "description": "Interest rate passed through to investors", 
                "aggregation_function": AggregationFunction.AVG,  # Will be 1 record per tranche
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_pass_thru_rte",
                "group_level": GroupLevel.TRANCHE
            },
            {
                "name": "Interest Distribution Amount",
                "description": "Interest distributed to investors",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_int_dstrb_amt",
                "group_level": GroupLevel.TRANCHE
            },
            {
                "name": "Principal Distribution Amount", 
                "description": "Principal distributed to investors",
                "aggregation_function": AggregationFunction.SUM,
                "source_model": SourceModel.TRANCHE_BAL,
                "source_field": "tr_prin_dstrb_amt",
                "group_level": GroupLevel.TRANCHE
            }
        ]
        
        # Create all calculations
        all_calculations = []
        
        # Add RAW field calculations
        for field_data in deal_raw_fields + tranche_raw_fields:
            calc = Calculation(
                name=field_data["name"],
                description=field_data["description"],
                aggregation_function=AggregationFunction.RAW,
                source_model=field_data["source_model"],
                source_field=field_data["source_field"],
                group_level=field_data["group_level"],
                created_by="system"
            )
            all_calculations.append(calc)
        
        # Add aggregated calculations
        for field_data in deal_aggregated + tranche_aggregated:
            calc = Calculation(
                name=field_data["name"],
                description=field_data["description"],
                aggregation_function=field_data["aggregation_function"],
                source_model=field_data["source_model"],
                source_field=field_data["source_field"],
                group_level=field_data["group_level"],
                weight_field=field_data.get("weight_field"),
                created_by="system"
            )
            all_calculations.append(calc)
        
        # Bulk insert
        config_db.add_all(all_calculations)
        config_db.commit()
        
        print(f"✅ Created {len(all_calculations)} standard calculations:")
        print(f"   📊 {len(deal_raw_fields + tranche_raw_fields)} RAW field calculations")
        print(f"   📈 {len(deal_aggregated + tranche_aggregated)} aggregated calculations")
        
        # Print breakdown by group level
        deal_count = len([c for c in all_calculations if c.group_level == GroupLevel.DEAL])
        tranche_count = len([c for c in all_calculations if c.group_level == GroupLevel.TRANCHE])
        print(f"   🎯 {deal_count} deal-level, {tranche_count} tranche-level calculations")
        
    except Exception as e:
        config_db.rollback()
        print(f"❌ Error creating standard calculations: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        config_db.close()


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
            
            # Show sample deal numbers for this issuer
            deal_numbers = [str(d.dl_nbr) for d in issuer_deals[:3]]
            if len(issuer_deals) > 3:
                deal_numbers.append(f"... +{len(issuer_deals) - 3} more")
            print(f"     Sample deals: {', '.join(deal_numbers)}")

        # Highlight the high-tranche deals for UI testing
        print(f"\n🎯 High-tranche deals for UI testing:")
        complex_deals = [d for d in created_deals if d.issr_cde == "COMPLEX24"]
        for deal in complex_deals:
            deal_tranches = [t for t in created_tranches if t.dl_nbr == deal.dl_nbr]
            print(f"   Deal {deal.dl_nbr} ({deal.cdi_file_nme}): {len(deal_tranches)} tranches")
            # Show first few and last few tranche IDs as a preview
            tranche_ids = [t.tr_id for t in deal_tranches]
            if len(tranche_ids) > 8:
                preview = ", ".join(tranche_ids[:4]) + f" ... {len(tranche_ids) - 8} more ... " + ", ".join(tranche_ids[-4:])
            else:
                preview = ", ".join(tranche_ids)
            print(f"     Tranches: {preview}")

        # Print deal number range
        print(f"\n📋 Deal number range: {min(d.dl_nbr for d in created_deals)} - {max(d.dl_nbr for d in created_deals)}")
        
        # Print unique tranche IDs by issuer
        print(f"\n📈 Tranche patterns by issuer:")
        for issuer in issuers_config:
            issuer_deals = [d for d in created_deals if d.issr_cde == issuer["issuer_code"]]
            issuer_tranches = [t for t in created_tranches if any(d.dl_nbr == t.dl_nbr for d in issuer_deals)]
            tranche_ids = sorted(set(t.tr_id for t in issuer_tranches))
            if len(tranche_ids) > 10:
                preview = ", ".join(tranche_ids[:8]) + f" ... +{len(tranche_ids) - 8} more"
            else:
                preview = ", ".join(tranche_ids)
            print(f"   {issuer['issuer_code']}: {preview}")

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
    print("Initializing dual database system...")

    if force_recreate:
        print("🔄 Force recreate mode: Dropping existing tables...")
        drop_all_tables()

    # Create all tables
    create_all_tables()

    # Create standard calculations (must come before sample data)
    create_standard_calculations()

    # Create sample data for development
    create_sample_data()

    print("Database initialization complete!")


if __name__ == "__main__":
    # Allow running this file directly to initialize databases
    initialize_databases()