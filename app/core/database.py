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
    initialize_databases()


# ===== TABLE CREATION =====


def create_all_tables():
    """Create tables in both databases."""
    # Import models to ensure they're registered with Base classes
    from app.reporting.models import Report  # noqa: F401
    from app.datawarehouse.models import Deal, Tranche, Cycle  # noqa: F401

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
    from app.datawarehouse.models import Deal, Tranche, TrancheHistorical, Cycle
    from datetime import date
    from decimal import Decimal

    # Create data warehouse session
    dw_db = DWSessionLocal()

    try:
        # Check if sample data already exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 0:
            print(f"Sample data already exists ({existing_deals} deals found). Skipping creation.")
            return

        print("Creating comprehensive sample data...")

        # ===== SEED CYCLES TABLE FIRST =====
        print("Seeding cycles table...")
        cycles_data = [
            {
                "code": "12501",
                "description": "January 2023 Cycle",
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
            },
            {
                "code": "12502",
                "description": "February 2023 Cycle",
                "start_date": "2023-02-01",
                "end_date": "2023-02-28",
            },
            {
                "code": "12503",
                "description": "March 2023 Cycle",
                "start_date": "2023-03-01",
                "end_date": "2023-03-31",
            },
            {
                "code": "12504",
                "description": "April 2023 Cycle",
                "start_date": "2023-04-01",
                "end_date": "2023-04-30",
            },
            {
                "code": "12505",
                "description": "May 2023 Cycle",
                "start_date": "2023-05-01",
                "end_date": "2023-05-31",
            },
            {
                "code": "12506",
                "description": "June 2023 Cycle",
                "start_date": "2023-06-01",
                "end_date": "2023-06-30",
            },
        ]

        # Create cycles
        created_cycles = []
        for cycle_data in cycles_data:
            # Check if cycle already exists to avoid duplicates
            existing_cycle = dw_db.query(Cycle).filter(Cycle.code == cycle_data["code"]).first()
            if not existing_cycle:
                cycle = Cycle(**cycle_data)
                dw_db.add(cycle)
                created_cycles.append(cycle)
            else:
                created_cycles.append(existing_cycle)

        dw_db.flush()  # Flush to ensure cycles are saved before creating deals

        # Sample deals with realistic MBS data - no cycle_code in new model
        deals_data = [
            {
                "name": "GSAMP Trust 2024-1",
                "originator": "Goldman Sachs",
                "deal_type": "RMBS",
                "closing_date": date(2024, 1, 15),
                "total_principal": Decimal("2500000000"),
                "credit_rating": "AAA",
                "yield_rate": Decimal("0.0485"),
                "duration": Decimal("5.5"),
            },
            {
                "name": "Wells Fargo Commercial 2024-A",
                "originator": "Wells Fargo",
                "deal_type": "CMBS",
                "closing_date": date(2024, 2, 20),
                "total_principal": Decimal("1800000000"),
                "credit_rating": "AA+",
                "yield_rate": Decimal("0.0520"),
                "duration": Decimal("7.0"),
            },
            {
                "name": "Chase Auto Receivables 2024-1",
                "originator": "JPMorgan Chase",
                "deal_type": "Auto ABS",
                "closing_date": date(2024, 3, 10),
                "total_principal": Decimal("1200000000"),
                "credit_rating": "AAA",
                "yield_rate": Decimal("0.0395"),
                "duration": Decimal("3.5"),
            },
            {
                "name": "Bank of America RMBS 2024-2",
                "originator": "Bank of America",
                "deal_type": "RMBS",
                "closing_date": date(2024, 1, 25),
                "total_principal": Decimal("3200000000"),
                "credit_rating": "AA",
                "yield_rate": Decimal("0.0510"),
                "duration": Decimal("6.2"),
            },
            {
                "name": "Citi Student Loan Trust 2024-A",
                "originator": "Citibank",
                "deal_type": "Student Loan ABS",
                "closing_date": date(2024, 2, 15),
                "total_principal": Decimal("950000000"),
                "credit_rating": "AA-",
                "yield_rate": Decimal("0.0465"),
                "duration": Decimal("8.1"),
            },
            {
                "name": "Morgan Stanley CMBS 2024-B",
                "originator": "Morgan Stanley",
                "deal_type": "CMBS",
                "closing_date": date(2024, 3, 5),
                "total_principal": Decimal("2100000000"),
                "credit_rating": "AAA",
                "yield_rate": Decimal("0.0535"),
                "duration": Decimal("6.8"),
            },
        ]

        # Create deals
        created_deals = []
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
            created_deals.append(deal)

        dw_db.flush()  # Flush to get IDs but don't commit yet

        # Define tranches for each deal - removing principal_amount, interest_rate, cycle_code from tranche data
        tranches_data = []

        # GSAMP Trust 2024-1 tranches (Deal 0)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class A-1",
                    "class_name": "A-1",
                    "subordination_level": 1,
                    "credit_rating": "AAA",
                    "payment_priority": 1,
                },
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class A-2",
                    "class_name": "A-2",
                    "subordination_level": 1,
                    "credit_rating": "AAA",
                    "payment_priority": 2,
                },
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "credit_rating": "AA",
                    "payment_priority": 3,
                },
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "credit_rating": "A",
                    "payment_priority": 4,
                },
            ]
        )

        # Wells Fargo Commercial 2024-A tranches (Deal 1)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[1].id,
                    "name": "Senior A",
                    "class_name": "A",
                    "subordination_level": 1,
                    "credit_rating": "AA+",
                    "payment_priority": 1,
                },
                {
                    "deal_id": created_deals[1].id,
                    "name": "Subordinate B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "credit_rating": "A",
                    "payment_priority": 2,
                },
                {
                    "deal_id": created_deals[1].id,
                    "name": "Junior C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "credit_rating": "BBB",
                    "payment_priority": 3,
                },
            ]
        )

        # Chase Auto Receivables 2024-1 tranches (Deal 2)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[2].id,
                    "name": "Class A",
                    "class_name": "A",
                    "subordination_level": 1,
                    "credit_rating": "AAA",
                    "payment_priority": 1,
                },
                {
                    "deal_id": created_deals[2].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "credit_rating": "AA",
                    "payment_priority": 2,
                },
                {
                    "deal_id": created_deals[2].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "credit_rating": "A",
                    "payment_priority": 3,
                },
            ]
        )

        # Bank of America RMBS 2024-2 tranches (Deal 3)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class A-1",
                    "class_name": "A-1",
                    "subordination_level": 1,
                    "credit_rating": "AA",
                    "payment_priority": 1,
                },
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class A-2",
                    "class_name": "A-2",
                    "subordination_level": 1,
                    "credit_rating": "AA",
                    "payment_priority": 2,
                },
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "credit_rating": "A",
                    "payment_priority": 3,
                },
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "credit_rating": "BBB",
                    "payment_priority": 4,
                },
            ]
        )

        # Citi Student Loan Trust 2024-A tranches (Deal 4)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[4].id,
                    "name": "Class A",
                    "class_name": "A",
                    "subordination_level": 1,
                    "credit_rating": "AA-",
                    "payment_priority": 1,
                },
                {
                    "deal_id": created_deals[4].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "credit_rating": "A",
                    "payment_priority": 2,
                },
                {
                    "deal_id": created_deals[4].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "credit_rating": "BBB",
                    "payment_priority": 3,
                },
            ]
        )

        # Morgan Stanley CMBS 2024-B tranches (Deal 5)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class A-1",
                    "class_name": "A-1",
                    "subordination_level": 1,
                    "credit_rating": "AAA",
                    "payment_priority": 1,
                },
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class A-2",
                    "class_name": "A-2",
                    "subordination_level": 1,
                    "credit_rating": "AAA",
                    "payment_priority": 2,
                },
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "credit_rating": "AA",
                    "payment_priority": 3,
                },
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "credit_rating": "A",
                    "payment_priority": 4,
                },
            ]
        )

        # Create all tranches
        created_tranches = []
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)
            dw_db.flush()  # Flush to get the ID
            created_tranches.append(tranche)

        # Define historical data for tranches across cycles
        tranche_historical_data = []

        # Historical data mapping - a dictionary of tranche position (in created_tranches) to principal/interest values
        tranche_values = {
            # GSAMP Trust tranches
            0: {"principal": Decimal("1500000000"), "interest": Decimal("0.0450")},
            1: {"principal": Decimal("750000000"), "interest": Decimal("0.0485")},
            2: {"principal": Decimal("200000000"), "interest": Decimal("0.0650")},
            3: {"principal": Decimal("50000000"), "interest": Decimal("0.0950")},
            # Wells Fargo tranches
            4: {"principal": Decimal("1260000000"), "interest": Decimal("0.0500")},
            5: {"principal": Decimal("360000000"), "interest": Decimal("0.0720")},
            6: {"principal": Decimal("180000000"), "interest": Decimal("0.1050")},
            # Chase Auto tranches
            7: {"principal": Decimal("960000000"), "interest": Decimal("0.0375")},
            8: {"principal": Decimal("180000000"), "interest": Decimal("0.0480")},
            9: {"principal": Decimal("60000000"), "interest": Decimal("0.0750")},
            # Bank of America tranches
            10: {"principal": Decimal("2000000000"), "interest": Decimal("0.0490")},
            11: {"principal": Decimal("900000000"), "interest": Decimal("0.0520")},
            12: {"principal": Decimal("250000000"), "interest": Decimal("0.0680")},
            13: {"principal": Decimal("50000000"), "interest": Decimal("0.0920")},
            # Citi Student Loan tranches
            14: {"principal": Decimal("760000000"), "interest": Decimal("0.0445")},
            15: {"principal": Decimal("142500000"), "interest": Decimal("0.0580")},
            16: {"principal": Decimal("47500000"), "interest": Decimal("0.0820")},
            # Morgan Stanley tranches
            17: {"principal": Decimal("1470000000"), "interest": Decimal("0.0515")},
            18: {"principal": Decimal("420000000"), "interest": Decimal("0.0550")},
            19: {"principal": Decimal("147000000"), "interest": Decimal("0.0750")},
            20: {"principal": Decimal("63000000"), "interest": Decimal("0.0980")},
        }

        # Initial cycle allocation - which deal's tranches belong to which initial cycle
        deal_cycles = {
            0: "12501",  # GSAMP Trust - January 2023
            1: "12502",  # Wells Fargo - February 2023
            2: "12503",  # Chase Auto - March 2023
            3: "12501",  # Bank of America - January 2023
            4: "12502",  # Citi Student Loan - February 2023
            5: "12503",  # Morgan Stanley - March 2023
        }

        # Create historical records for each tranche in its initial cycle
        print("Creating initial historical records...")
        for i, tranche in enumerate(created_tranches):
            deal_idx = None
            for deal_idx in range(len(created_deals)):
                if tranche.deal_id == created_deals[deal_idx].id:
                    break

            if deal_idx is not None:
                cycle_code = deal_cycles[deal_idx]
                historical = TrancheHistorical(
                    tranche_id=tranche.id,
                    cycle_code=cycle_code,
                    principal_amount=tranche_values[i]["principal"],
                    interest_rate=tranche_values[i]["interest"],
                )
                dw_db.add(historical)
                tranche_historical_data.append(historical)

        # Create additional cycle data for all tranches
        print("Creating historical data across additional cycles...")
        additional_cycles = ["12504", "12505", "12506"]  # Additional cycles

        for tranche_idx, tranche in enumerate(created_tranches):
            base_principal = tranche_values[tranche_idx]["principal"]
            base_interest = tranche_values[tranche_idx]["interest"]

            for i, cycle in enumerate(additional_cycles):
                # Simulate amortization and interest rate drift
                amortization_factor = Decimal("0.97") ** (i + 1)  # Progressive reduction
                interest_drift = Decimal("0.0005") * (i + 1)  # Progressive increase

                historical = TrancheHistorical(
                    tranche_id=tranche.id,
                    cycle_code=cycle,
                    principal_amount=base_principal * amortization_factor,
                    interest_rate=base_interest + interest_drift,
                )
                dw_db.add(historical)
                tranche_historical_data.append(historical)

        # Commit everything
        dw_db.commit()

        print(f"✅ Successfully created:")
        print(f"   🗓️  {len(created_cycles)} cycles")
        print(f"   📊 {len(created_deals)} deals")
        print(f"   📈 {len(created_tranches)} tranches")
        print(f"   📊 {len(tranche_historical_data)} historical records")
        print(f"   Across cycles: {', '.join([c.code for c in created_cycles])}")

        # Print summary by cycle
        print(f"\n📋 Summary by cycle:")
        all_cycle_codes = [c.code for c in created_cycles]
        for cycle in all_cycle_codes:
            cycle_historical = [h for h in tranche_historical_data if h.cycle_code == cycle]
            print(f"   {cycle}: {len(cycle_historical)} historical tranche records")

    except Exception as e:
        dw_db.rollback()
        print(f"❌ Error creating sample data: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        dw_db.close()


# ===== INITIALIZATION FUNCTION =====


def initialize_databases():
    """Initialize both databases with tables and sample data."""
    print("Initializing dual database system...")

    # Create all tables
    create_all_tables()

    # Create sample data for development
    create_sample_data()

    print("Database initialization complete!")


if __name__ == "__main__":
    # Allow running this file directly to initialize databases
    initialize_databases()
