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
    from app.datawarehouse.models import Deal, Tranche  # noqa: F401

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
    from app.datawarehouse.models import Deal, Tranche
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

        # Sample deals with realistic MBS data
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
                "cycle_code": "2024-01",
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
                "cycle_code": "2024-02",
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
                "cycle_code": "2024-03",
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
                "cycle_code": "2024-01",
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
                "cycle_code": "2024-02",
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
                "cycle_code": "2024-03",
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

        # GSAMP Trust 2024-1 tranches (Deal 0)
        tranches_data.extend(
            [
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class A-1",
                    "class_name": "A-1",
                    "subordination_level": 1,
                    "principal_amount": Decimal("1500000000"),
                    "interest_rate": Decimal("0.0450"),
                    "credit_rating": "AAA",
                    "payment_priority": 1,
                    "cycle_code": "2024-01",
                },
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class A-2",
                    "class_name": "A-2",
                    "subordination_level": 1,
                    "principal_amount": Decimal("750000000"),
                    "interest_rate": Decimal("0.0485"),
                    "credit_rating": "AAA",
                    "payment_priority": 2,
                    "cycle_code": "2024-01",
                },
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "principal_amount": Decimal("200000000"),
                    "interest_rate": Decimal("0.0650"),
                    "credit_rating": "AA",
                    "payment_priority": 3,
                    "cycle_code": "2024-01",
                },
                {
                    "deal_id": created_deals[0].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "principal_amount": Decimal("50000000"),
                    "interest_rate": Decimal("0.0950"),
                    "credit_rating": "A",
                    "payment_priority": 4,
                    "cycle_code": "2024-01",
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
                    "principal_amount": Decimal("1260000000"),
                    "interest_rate": Decimal("0.0500"),
                    "credit_rating": "AA+",
                    "payment_priority": 1,
                    "cycle_code": "2024-02",
                },
                {
                    "deal_id": created_deals[1].id,
                    "name": "Subordinate B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "principal_amount": Decimal("360000000"),
                    "interest_rate": Decimal("0.0720"),
                    "credit_rating": "A",
                    "payment_priority": 2,
                    "cycle_code": "2024-02",
                },
                {
                    "deal_id": created_deals[1].id,
                    "name": "Junior C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "principal_amount": Decimal("180000000"),
                    "interest_rate": Decimal("0.1050"),
                    "credit_rating": "BBB",
                    "payment_priority": 3,
                    "cycle_code": "2024-02",
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
                    "principal_amount": Decimal("960000000"),
                    "interest_rate": Decimal("0.0375"),
                    "credit_rating": "AAA",
                    "payment_priority": 1,
                    "cycle_code": "2024-03",
                },
                {
                    "deal_id": created_deals[2].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "principal_amount": Decimal("180000000"),
                    "interest_rate": Decimal("0.0480"),
                    "credit_rating": "AA",
                    "payment_priority": 2,
                    "cycle_code": "2024-03",
                },
                {
                    "deal_id": created_deals[2].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "principal_amount": Decimal("60000000"),
                    "interest_rate": Decimal("0.0750"),
                    "credit_rating": "A",
                    "payment_priority": 3,
                    "cycle_code": "2024-03",
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
                    "principal_amount": Decimal("2000000000"),
                    "interest_rate": Decimal("0.0490"),
                    "credit_rating": "AA",
                    "payment_priority": 1,
                    "cycle_code": "2024-01",
                },
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class A-2",
                    "class_name": "A-2",
                    "subordination_level": 1,
                    "principal_amount": Decimal("900000000"),
                    "interest_rate": Decimal("0.0520"),
                    "credit_rating": "AA",
                    "payment_priority": 2,
                    "cycle_code": "2024-01",
                },
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "principal_amount": Decimal("250000000"),
                    "interest_rate": Decimal("0.0680"),
                    "credit_rating": "A",
                    "payment_priority": 3,
                    "cycle_code": "2024-01",
                },
                {
                    "deal_id": created_deals[3].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "principal_amount": Decimal("50000000"),
                    "interest_rate": Decimal("0.0920"),
                    "credit_rating": "BBB",
                    "payment_priority": 4,
                    "cycle_code": "2024-01",
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
                    "principal_amount": Decimal("760000000"),
                    "interest_rate": Decimal("0.0445"),
                    "credit_rating": "AA-",
                    "payment_priority": 1,
                    "cycle_code": "2024-02",
                },
                {
                    "deal_id": created_deals[4].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "principal_amount": Decimal("142500000"),
                    "interest_rate": Decimal("0.0580"),
                    "credit_rating": "A",
                    "payment_priority": 2,
                    "cycle_code": "2024-02",
                },
                {
                    "deal_id": created_deals[4].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "principal_amount": Decimal("47500000"),
                    "interest_rate": Decimal("0.0820"),
                    "credit_rating": "BBB",
                    "payment_priority": 3,
                    "cycle_code": "2024-02",
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
                    "principal_amount": Decimal("1470000000"),
                    "interest_rate": Decimal("0.0515"),
                    "credit_rating": "AAA",
                    "payment_priority": 1,
                    "cycle_code": "2024-03",
                },
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class A-2",
                    "class_name": "A-2",
                    "subordination_level": 1,
                    "principal_amount": Decimal("420000000"),
                    "interest_rate": Decimal("0.0550"),
                    "credit_rating": "AAA",
                    "payment_priority": 2,
                    "cycle_code": "2024-03",
                },
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class B",
                    "class_name": "B",
                    "subordination_level": 2,
                    "principal_amount": Decimal("147000000"),
                    "interest_rate": Decimal("0.0750"),
                    "credit_rating": "AA",
                    "payment_priority": 3,
                    "cycle_code": "2024-03",
                },
                {
                    "deal_id": created_deals[5].id,
                    "name": "Class C",
                    "class_name": "C",
                    "subordination_level": 3,
                    "principal_amount": Decimal("63000000"),
                    "interest_rate": Decimal("0.0980"),
                    "credit_rating": "A",
                    "payment_priority": 4,
                    "cycle_code": "2024-03",
                },
            ]
        )

        # Create all tranches
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)

            # Replicate each tranche across additional cycles to simulate monthly updates
        additional_cycles = ["2024-04", "2024-05", "2024-06"]
        expanded_tranches = []

        for tranche_data in tranches_data:
            for cycle in additional_cycles:
                new_tranche = tranche_data.copy()
                new_tranche["cycle_code"] = cycle
                # Simulate principal amortization and interest rate drift
                new_tranche["principal_amount"] = new_tranche["principal_amount"] * Decimal("0.97")
                new_tranche["interest_rate"] = new_tranche["interest_rate"] + Decimal("0.0005")
                expanded_tranches.append(new_tranche)

        # Combine all tranches
        tranches_data.extend(expanded_tranches)

        # Commit everything
        dw_db.commit()

        print(f"✅ Successfully created:")
        print(f"   📊 {len(created_deals)} deals")
        print(f"   📈 {len(tranches_data)} tranches")
        print(f"   🗓️  Across 3 cycles (2024-01, 2024-02, 2024-03)")

        # Print summary by cycle
        print(f"\n📋 Summary by cycle:")
        for cycle in ["2024-01", "2024-02", "2024-03"]:
            cycle_deals = [d for d in created_deals if d.cycle_code == cycle]
            cycle_tranches = [t for t in tranches_data if t["cycle_code"] == cycle]
            print(f"   {cycle}: {len(cycle_deals)} deals, {len(cycle_tranches)} tranches")

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
