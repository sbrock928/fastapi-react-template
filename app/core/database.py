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

        print("Creating comprehensive sample data with hundreds of deals...")

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
            {
                "code": "12507",
                "description": "July 2023 Cycle",
                "start_date": "2023-07-01",
                "end_date": "2023-07-31",
            },
            {
                "code": "12508",
                "description": "August 2023 Cycle",
                "start_date": "2023-08-01",
                "end_date": "2023-08-31",
            },
            {
                "code": "12509",
                "description": "September 2023 Cycle",
                "start_date": "2023-09-01",
                "end_date": "2023-09-30",
            },
            {
                "code": "12510",
                "description": "October 2023 Cycle",
                "start_date": "2023-10-01",
                "end_date": "2023-10-31",
            },
            {
                "code": "12511",
                "description": "November 2023 Cycle",
                "start_date": "2023-11-01",
                "end_date": "2023-11-30",
            },
            {
                "code": "12512",
                "description": "December 2023 Cycle",
                "start_date": "2023-12-01",
                "end_date": "2023-12-31",
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

        # Define deal templates and configurations for generating hundreds of deals
        originators = {
            "RMBS": [
                "Goldman Sachs", "Bank of America", "Wells Fargo", "JPMorgan Chase", "Citibank",
                "Morgan Stanley", "UBS", "Freddie Mac", "Fannie Mae", "Credit Suisse",
                "Deutsche Bank", "Barclays", "HSBC", "RBC", "Nomura Securities",
                "Mizuho Securities", "Societe Generale", "BNP Paribas", "ING", "Santander"
            ],
            "CMBS": [
                "Wells Fargo", "Morgan Stanley", "Deutsche Bank", "Credit Suisse", "Goldman Sachs",
                "Barclays", "UBS", "Bank of America", "JPMorgan Chase", "Citibank",
                "HSBC", "RBC", "Nomura Securities", "Mizuho Securities", "KeyBank",
                "PNC Bank", "Regions Bank", "Fifth Third Bank", "SunTrust", "BB&T"
            ],
            "Auto ABS": [
                "JPMorgan Chase", "Ford Motor Credit", "General Motors Financial", "Ally Financial",
                "Toyota Motor Credit", "Honda Finance", "Nissan Motor Acceptance", "BMW Financial",
                "Mercedes-Benz Financial", "Volkswagen Credit", "Hyundai Motor Finance",
                "Capital One Auto Finance", "Wells Fargo Dealer Services", "Santander Consumer",
                "Credit Acceptance", "American Credit Acceptance", "Westlake Financial",
                "DriveTime", "Carvana", "Vroom Financial"
            ],
            "Student Loan ABS": [
                "Citibank", "Navient", "Sallie Mae", "Wells Fargo", "Discover Financial",
                "PNC Bank", "SunTrust", "Citizens Bank", "Great Lakes", "FedLoan Servicing",
                "MOHELA", "Nelnet", "OSLA Servicing", "EdFinancial", "HESC", "PHEAA",
                "KHEAA", "VSAC", "RISLA", "SELF"
            ],
            "Credit Card ABS": [
                "Capital One", "JPMorgan Chase", "American Express", "Bank of America",
                "Citibank", "Wells Fargo", "Discover Financial", "Synchrony Financial",
                "Barclays", "HSBC", "TD Bank", "PNC Bank", "U.S. Bank", "Regions Bank",
                "Fifth Third Bank", "KeyBank", "SunTrust", "BB&T", "First National Bank",
                "BMO Harris Bank"
            ],
            "Equipment ABS": [
                "Dell Financial Services", "Caterpillar Financial", "John Deere Financial",
                "CNH Industrial Capital", "Kubota Credit", "Case New Holland", "AGCO Finance",
                "Volvo Financial Services", "Paccar Financial", "Navistar Financial",
                "Komatsu Financial", "Hitachi Capital", "JCB Finance", "Liebherr Financial",
                "Bobcat Financial", "Terex Financial Services", "Manitowoc Finance",
                "Link-Belt Financial", "Tadano Financial", "Grove Financial"
            ],
            "Equipment Lease ABS": [
                "GE Capital", "Caterpillar Financial", "John Deere Financial", "Wells Fargo Equipment Finance",
                "Bank of America Equipment Finance", "PNC Equipment Finance", "U.S. Bank Equipment Finance",
                "KeyBank Equipment Finance", "Fifth Third Equipment Finance", "Regions Equipment Finance",
                "SunTrust Equipment Finance", "BB&T Equipment Finance", "First National Equipment Finance",
                "BMO Harris Equipment Finance", "TD Equipment Finance", "RBC Equipment Finance",
                "CIBC Equipment Finance", "Scotia Equipment Finance", "Hitachi Capital Equipment Finance",
                "Kubota Credit Equipment Finance"
            ],
            "Personal Loan ABS": [
                "LendingClub", "Prosper", "Upstart", "SoFi", "Marcus by Goldman Sachs",
                "Avant", "OneMain Financial", "Rocket Loans", "LightStream", "Payoff",
                "Best Egg", "Earnest", "Figure", "Peerform", "Funding Circle",
                "Kiva Microfunds", "Zopa", "RateSetter", "Funding Societies", "Mintos"
            ],
            "Marketplace Loan ABS": [
                "LendingClub", "Prosper", "Upstart", "Funding Circle", "OnDeck",
                "Kabbage", "BlueVine", "Fundbox", "Square Capital", "PayPal Working Capital",
                "Amazon Lending", "eBay Managed Delivery", "Stripe Capital", "Shopify Capital",
                "BigCommerce Capital", "WooCommerce Capital", "Magento Commerce Capital",
                "PrestaShop Capital", "OpenCart Capital", "Zen Cart Capital"
            ]
        }

        # Credit rating distributions by deal type
        credit_rating_distributions = {
            "RMBS": ["AAA"] * 40 + ["AA+"] * 25 + ["AA"] * 20 + ["AA-"] * 10 + ["A+"] * 3 + ["A"] * 2,
            "CMBS": ["AAA"] * 30 + ["AA+"] * 25 + ["AA"] * 25 + ["AA-"] * 15 + ["A+"] * 3 + ["A"] * 2,
            "Auto ABS": ["AAA"] * 50 + ["AA+"] * 30 + ["AA"] * 15 + ["AA-"] * 5,
            "Student Loan ABS": ["AA"] * 30 + ["AA-"] * 25 + ["A+"] * 20 + ["A"] * 15 + ["A-"] * 8 + ["BBB+"] * 2,
            "Credit Card ABS": ["AAA"] * 60 + ["AA+"] * 25 + ["AA"] * 10 + ["AA-"] * 5,
            "Equipment ABS": ["AA+"] * 30 + ["AA"] * 35 + ["AA-"] * 20 + ["A+"] * 10 + ["A"] * 5,
            "Equipment Lease ABS": ["AA"] * 40 + ["AA-"] * 30 + ["A+"] * 20 + ["A"] * 10,
            "Personal Loan ABS": ["A"] * 40 + ["A-"] * 30 + ["BBB+"] * 20 + ["BBB"] * 10,
            "Marketplace Loan ABS": ["A-"] * 30 + ["BBB+"] * 30 + ["BBB"] * 25 + ["BBB-"] * 15
        }

        # Generate hundreds of deals
        print("Generating hundreds of deals...")
        deals_data = []
        
        # Helper function to generate realistic deal data
        def generate_deal_data(deal_type, index, year=2024):
            originators_list = originators[deal_type]
            originator = random.choice(originators_list)
            
            # Deal size ranges by type (in millions)
            size_ranges = {
                "RMBS": (500, 5000),
                "CMBS": (300, 3000),
                "Auto ABS": (400, 2000),
                "Student Loan ABS": (200, 1500),
                "Credit Card ABS": (800, 3500),
                "Equipment ABS": (150, 1200),
                "Equipment Lease ABS": (100, 800),
                "Personal Loan ABS": (50, 500),
                "Marketplace Loan ABS": (25, 300)
            }
            
            min_size, max_size = size_ranges[deal_type]
            principal = Decimal(str(random.randint(min_size, max_size) * 1000000))
            
            # Yield rates by type (base rates)
            yield_ranges = {
                "RMBS": (0.0350, 0.0550),
                "CMBS": (0.0400, 0.0650),
                "Auto ABS": (0.0300, 0.0500),
                "Student Loan ABS": (0.0400, 0.0700),
                "Credit Card ABS": (0.0350, 0.0550),
                "Equipment ABS": (0.0450, 0.0700),
                "Equipment Lease ABS": (0.0400, 0.0650),
                "Personal Loan ABS": (0.0600, 0.1200),
                "Marketplace Loan ABS": (0.0800, 0.1500)
            }
            
            min_yield, max_yield = yield_ranges[deal_type]
            yield_rate = Decimal(str(round(random.uniform(min_yield, max_yield), 4)))
            
            # Duration ranges by type
            duration_ranges = {
                "RMBS": (4.0, 8.0),
                "CMBS": (5.0, 10.0),
                "Auto ABS": (2.0, 5.0),
                "Student Loan ABS": (6.0, 12.0),
                "Credit Card ABS": (1.0, 3.0),
                "Equipment ABS": (3.0, 7.0),
                "Equipment Lease ABS": (2.0, 6.0),
                "Personal Loan ABS": (2.0, 7.0),
                "Marketplace Loan ABS": (1.0, 5.0)
            }
            
            min_duration, max_duration = duration_ranges[deal_type]
            duration = Decimal(str(round(random.uniform(min_duration, max_duration), 1)))
            
            # Random closing date within the year
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            random_days = random.randint(0, (end_date - start_date).days)
            closing_date = start_date + timedelta(days=random_days)
            
            # Credit rating
            credit_rating = random.choice(credit_rating_distributions[deal_type])
            
            # Deal naming convention
            deal_names = {
                "RMBS": f"{originator.split()[0]} RMBS {year}-{index}",
                "CMBS": f"{originator.split()[0]} CMBS {year}-{chr(65 + index % 26)}",
                "Auto ABS": f"{originator.split()[0]} Auto Receivables {year}-{index}",
                "Student Loan ABS": f"{originator.split()[0]} Student Loan Trust {year}-{chr(65 + index % 26)}",
                "Credit Card ABS": f"{originator.split()[0]} Credit Card {year}-{index}",
                "Equipment ABS": f"{originator.split()[0]} Equipment Finance {year}-{index}",
                "Equipment Lease ABS": f"{originator.split()[0]} Equipment Lease {year}-{chr(65 + index % 26)}",
                "Personal Loan ABS": f"{originator.split()[0]} Personal Loan {year}-{index}",
                "Marketplace Loan ABS": f"{originator.split()[0]} Marketplace {year}-{index}"
            }
            
            return {
                "name": deal_names[deal_type],
                "originator": originator,
                "deal_type": deal_type,
                "closing_date": closing_date,
                "total_principal": principal,
                "credit_rating": credit_rating,
                "yield_rate": yield_rate,
                "duration": duration,
            }

        # Generate deals by type with realistic distributions
        deal_type_counts = {
            "RMBS": 80,
            "CMBS": 60,
            "Auto ABS": 45,
            "Student Loan ABS": 35,
            "Credit Card ABS": 40,
            "Equipment ABS": 30,
            "Equipment Lease ABS": 25,
            "Personal Loan ABS": 20,
            "Marketplace Loan ABS": 15
        }

        # Generate for multiple years
        for year in [2022, 2023, 2024]:
            for deal_type, count in deal_type_counts.items():
                yearly_count = count if year == 2024 else int(count * 0.7)  # Fewer deals in previous years
                for i in range(yearly_count):
                    deal_data = generate_deal_data(deal_type, i + 1, year)
                    deals_data.append(deal_data)

        print(f"Generated {len(deals_data)} deals across multiple asset classes")

        # Create deals
        created_deals = []
        for deal_data in deals_data:
            deal = Deal(**deal_data)
            dw_db.add(deal)
            created_deals.append(deal)

        dw_db.flush()  # Flush to get IDs but don't commit yet

        # Define standard tranche configurations by deal type
        tranche_configs = {
            "RMBS": [
                {"name": "Class A-1", "class_name": "A-1", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class A-2", "class_name": "A-2", "subordination_level": 1, "payment_priority": 2},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 3},
                {"name": "Class C", "class_name": "C", "subordination_level": 3, "payment_priority": 4},
            ],
            "CMBS": [
                {"name": "Class A-1", "class_name": "A-1", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class A-2", "class_name": "A-2", "subordination_level": 1, "payment_priority": 2},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 3},
                {"name": "Class C", "class_name": "C", "subordination_level": 3, "payment_priority": 4},
            ],
            "Auto ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
                {"name": "Class C", "class_name": "C", "subordination_level": 3, "payment_priority": 3},
            ],
            "Student Loan ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
                {"name": "Class C", "class_name": "C", "subordination_level": 3, "payment_priority": 3},
                {"name": "Class D", "class_name": "D", "subordination_level": 4, "payment_priority": 4},
            ],
            "Credit Card ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
            ],
            "Equipment ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
                {"name": "Class C", "class_name": "C", "subordination_level": 3, "payment_priority": 3},
            ],
            "Equipment Lease ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
            ],
            "Personal Loan ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
                {"name": "Class C", "class_name": "C", "subordination_level": 3, "payment_priority": 3},
            ],
            "Marketplace Loan ABS": [
                {"name": "Class A", "class_name": "A", "subordination_level": 1, "payment_priority": 1},
                {"name": "Class B", "class_name": "B", "subordination_level": 2, "payment_priority": 2},
            ]
        }

        # Credit rating assignments by tranche class and deal type
        tranche_credit_ratings = {
            "RMBS": {"A-1": "AAA", "A-2": "AAA", "B": "AA", "C": "A"},
            "CMBS": {"A-1": "AAA", "A-2": "AAA", "B": "AA", "C": "A"},
            "Auto ABS": {"A": "AAA", "B": "AA", "C": "A"},
            "Student Loan ABS": {"A": "AA-", "B": "A", "C": "BBB+", "D": "BBB"},
            "Credit Card ABS": {"A": "AAA", "B": "AA"},
            "Equipment ABS": {"A": "AA", "B": "A", "C": "BBB"},
            "Equipment Lease ABS": {"A": "AA", "B": "A"},
            "Personal Loan ABS": {"A": "A", "B": "BBB+", "C": "BBB"},
            "Marketplace Loan ABS": {"A": "A-", "B": "BBB+"}
        }

        # Generate tranches for all deals
        print("Generating tranches for all deals...")
        tranches_data = []
        
        for deal in created_deals:
            deal_type = deal.deal_type
            configs = tranche_configs.get(deal_type, tranche_configs["RMBS"])  # Default to RMBS structure
            
            for config in configs:
                tranche_data = {
                    "deal_id": deal.id,
                    "name": config["name"],
                    "class_name": config["class_name"],
                    "subordination_level": config["subordination_level"],
                    "payment_priority": config["payment_priority"],
                    "credit_rating": tranche_credit_ratings[deal_type][config["class_name"]]
                }
                tranches_data.append(tranche_data)

        # Create all tranches
        created_tranches = []
        for tranche_data in tranches_data:
            tranche = Tranche(**tranche_data)
            dw_db.add(tranche)
            dw_db.flush()  # Flush to get the ID
            created_tranches.append(tranche)

        print(f"Generated {len(created_tranches)} tranches")

        # Generate historical data for all tranches across all cycles
        print("Generating historical data across all cycles...")
        
        # Helper function to generate realistic principal amounts and interest rates
        def get_tranche_values(deal, tranche):
            deal_principal = deal.total_principal
            
            # Define allocation percentages by tranche class
            allocations = {
                "A-1": 0.60, "A-2": 0.25, "A-3": 0.10, "A": 0.85,
                "B": 0.10, "C": 0.04, "D": 0.01
            }
            
            allocation = allocations.get(tranche.class_name, 0.05)
            principal = deal_principal * Decimal(str(allocation))
            
            # Add randomization based on deal and tranche IDs for consistency
            randomization = Decimal("0.9") + (Decimal("0.2") * Decimal(str((deal.id + tranche.id) % 10 / 10)))
            principal = principal * randomization
            
            # Base interest rates by credit rating
            base_rates = {
                "AAA": 0.0420, "AA+": 0.0450, "AA": 0.0480, "AA-": 0.0510,
                "A+": 0.0540, "A": 0.0570, "A-": 0.0600,
                "BBB+": 0.0650, "BBB": 0.0700, "BBB-": 0.0750,
                "BB+": 0.0800, "BB": 0.0850
            }
            
            base_rate = base_rates.get(tranche.credit_rating, 0.0500)
            
            # Add spread based on deal type
            deal_type_spreads = {
                "RMBS": 0.0000, "CMBS": 0.0030, "Auto ABS": -0.0020,
                "Student Loan ABS": 0.0040, "Credit Card ABS": -0.0010, 
                "Equipment ABS": 0.0050, "Equipment Lease ABS": 0.0040,
                "Personal Loan ABS": 0.0200, "Marketplace Loan ABS": 0.0300
            }
            
            spread = deal_type_spreads.get(deal.deal_type, 0.0000)
            interest_rate = Decimal(str(base_rate + spread))
            
            return {"principal": principal, "interest": interest_rate}

        # Create historical records
        tranche_historical_data = []
        all_cycle_codes = [cycle.code for cycle in created_cycles]
        
        # Distribute deals across cycles more randomly
        for i, tranche in enumerate(created_tranches):
            deal = next(d for d in created_deals if d.id == tranche.deal_id)
            
            # Assign initial cycle based on deal closing date
            closing_month = deal.closing_date.month
            initial_cycle_idx = (closing_month - 1) if closing_month <= 12 else 0
            
            # Get tranche values
            values = get_tranche_values(deal, tranche)
            base_principal = values["principal"]
            base_interest = values["interest"]
            
            # Create data for cycles starting from the deal's initial cycle
            for cycle_offset, cycle_code in enumerate(all_cycle_codes[initial_cycle_idx:]):
                # Simulate amortization and interest rate drift
                amortization_factor = Decimal("0.985") ** cycle_offset  # Slower amortization
                interest_drift = Decimal("0.0001") * cycle_offset  # Slower drift
                
                historical = TrancheHistorical(
                    tranche_id=tranche.id,
                    cycle_code=cycle_code,
                    principal_amount=base_principal * amortization_factor,
                    interest_rate=base_interest + interest_drift,
                )
                dw_db.add(historical)
                tranche_historical_data.append(historical)

        # Commit everything
        print("Committing all data to database...")
        dw_db.commit()

        print(f"✅ Successfully created massive dataset:")
        print(f"   🗓️  {len(created_cycles)} cycles")
        print(f"   📊 {len(created_deals)} deals")
        print(f"   📈 {len(created_tranches)} tranches")
        print(f"   📊 {len(tranche_historical_data)} historical records")

        # Print summary by deal type
        print(f"\n📋 Summary by deal type:")
        deal_types = {}
        for deal in created_deals:
            deal_type = deal.deal_type
            if deal_type not in deal_types:
                deal_types[deal_type] = 0
            deal_types[deal_type] += 1
        
        for deal_type, count in sorted(deal_types.items()):
            print(f"   {deal_type}: {count} deals")

        # Print summary by year
        print(f"\n📋 Summary by year:")
        years = {}
        for deal in created_deals:
            year = deal.closing_date.year
            if year not in years:
                years[year] = 0
            years[year] += 1
        
        for year, count in sorted(years.items()):
            print(f"   {year}: {count} deals")

        print(f"\n🎯 Total dataset size: {len(created_deals)} deals, {len(created_tranches)} tranches, {len(tranche_historical_data)} historical records")

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
