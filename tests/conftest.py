"""
Test configuration and shared fixtures for the FastAPI React Template test suite.
Provides database setup, authentication, and common test utilities.
"""

import pytest
import asyncio
from typing import Generator, Dict, Any, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import datetime

# Import your app modules - Fixed import
from app.app import create_app
from app.core.database import Base, DWBase, get_db, get_dw_db
from app.datawarehouse.models import Deal, Tranche, TrancheBal
from app.calculations.models import UserCalculation, SystemCalculation, AggregationFunction, SourceModel, GroupLevel
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation


# ===== DATABASE SETUP =====

@pytest.fixture(scope="session")
def config_engine():
    """Create in-memory SQLite engine for config database"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import all config models to register them
    from app.calculations.models import UserCalculation, SystemCalculation  # noqa: F401
    from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation  # noqa: F401
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session") 
def dw_engine():
    """Create in-memory SQLite engine for data warehouse database"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import all datawarehouse models to register them
    from app.datawarehouse.models import Deal, Tranche, TrancheBal  # noqa: F401
    DWBase.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def config_db_session(config_engine):
    """Create a database session for config database"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=config_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()  # Rollback any uncommitted changes
        session.close()
        # Clean up all data after each test
        Base.metadata.drop_all(bind=config_engine)
        Base.metadata.create_all(bind=config_engine)


@pytest.fixture(scope="function")
def dw_db_session(dw_engine):
    """Create a database session for data warehouse database"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=dw_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()  # Rollback any uncommitted changes
        session.close()
        # Clean up all data after each test
        DWBase.metadata.drop_all(bind=dw_engine)
        DWBase.metadata.create_all(bind=dw_engine)


@pytest.fixture
def client(config_db_session, dw_db_session):
    """Create FastAPI test client with database overrides"""
    # Create the app instance using the factory function
    app = create_app()
    
    def override_get_db():
        try:
            yield config_db_session
        finally:
            pass

    def override_get_dw_db():
        try:
            yield dw_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_dw_db] = override_get_dw_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


# ===== EVENT LOOP FIXTURE =====

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===== SAMPLE DATA FIXTURES =====

@pytest.fixture
def sample_deals(dw_db_session) -> List[Deal]:
    """Create sample deals for testing"""
    deals = [
        Deal(dl_nbr=1001, issr_cde="FHLMC", cdi_file_nme="FHLMC_2024_01.cdi", CDB_cdi_file_nme="FHLMC_CDB_01.cdi"),
        Deal(dl_nbr=1002, issr_cde="GNMA", cdi_file_nme="GNMA_2024_01.cdi", CDB_cdi_file_nme="GNMA_CDB_01.cdi"),
        Deal(dl_nbr=1003, issr_cde="PRIVATE", cdi_file_nme="PRIVATE_2024_01.cdi", CDB_cdi_file_nme=None),
    ]
    
    for deal in deals:
        dw_db_session.add(deal)
    dw_db_session.commit()
    
    return deals


@pytest.fixture
def sample_tranches(dw_db_session, sample_deals) -> List[Tranche]:
    """Create sample tranches for testing"""
    tranches = []
    for deal in sample_deals:
        for tr_id in ["A", "B", "C"]:
            tranche = Tranche(
                dl_nbr=deal.dl_nbr, 
                tr_id=tr_id,
                tr_cusip_id=f"{deal.issr_cde[:4]}{tr_id}{str(deal.dl_nbr)[-3:]}"
            )
            tranches.append(tranche)
            dw_db_session.add(tranche)
    
    dw_db_session.commit()
    return tranches


@pytest.fixture
def sample_tranche_balances(dw_db_session, sample_tranches) -> List[TrancheBal]:
    """Create sample tranche balance data for testing"""
    balances = []
    cycles = [202401, 202402, 202403, 202404]
    
    for tranche in sample_tranches:
        for cycle in cycles:
            balance = TrancheBal(
                dl_nbr=tranche.dl_nbr,
                tr_id=tranche.tr_id,
                cycle_cde=cycle,
                tr_end_bal_amt=1000000.0 + (cycle * 100),
                tr_prin_rel_ls_amt=50000.0,
                tr_pass_thru_rte=0.05,
                tr_accrl_days=30,
                tr_int_dstrb_amt=25000.0,
                tr_prin_dstrb_amt=100000.0,
                tr_int_accrl_amt=10000.0,
                tr_int_shtfl_amt=5000.0
            )
            balances.append(balance)
            dw_db_session.add(balance)
    
    dw_db_session.commit()
    return balances


@pytest.fixture
def sample_user_calculations(config_db_session) -> List[UserCalculation]:
    """Create sample user calculations for testing"""
    calculations = [
        UserCalculation(
            name="Total Balance",
            description="Sum of ending balances",
            aggregation_function=AggregationFunction.SUM,
            source_model=SourceModel.TRANCHE_BAL,
            source_field="tr_end_bal_amt",
            group_level=GroupLevel.DEAL,
            created_by="test_user",
            is_active=True,
            approved_by="test_user",
            approval_date=datetime.now()
        ),
        UserCalculation(
            name="Average Rate", 
            description="Weighted average pass-through rate",
            aggregation_function=AggregationFunction.WEIGHTED_AVG,
            source_model=SourceModel.TRANCHE_BAL,
            source_field="tr_pass_thru_rte",
            weight_field="tr_end_bal_amt",
            group_level=GroupLevel.DEAL,
            created_by="test_user",
            is_active=True,
            approved_by="test_user",
            approval_date=datetime.now()
        ),
        UserCalculation(
            name="Tranche Balance",
            description="Individual tranche balance",
            aggregation_function=AggregationFunction.SUM,
            source_model=SourceModel.TRANCHE_BAL,
            source_field="tr_end_bal_amt",
            group_level=GroupLevel.TRANCHE,
            created_by="test_user",
            is_active=True,
            approved_by="test_user",
            approval_date=datetime.now()
        )
    ]
    
    for calc in calculations:
        config_db_session.add(calc)
    config_db_session.commit()
    
    return calculations


@pytest.fixture
def sample_system_calculations(config_db_session) -> List[SystemCalculation]:
    """Create sample system calculations for testing"""
    calculations = [
        SystemCalculation(
            name="Issuer Type",
            description="Categorize deals by issuer type",
            raw_sql="""
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
                        WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
                        ELSE 'Private'
                    END AS issuer_type
                FROM deal
            """,
            result_column_name="issuer_type",
            group_level=GroupLevel.DEAL,
            created_by="test_system",
            is_active=True,
            approved_by="test_system",
            approval_date=datetime.now()
        ),
        SystemCalculation(
            name="Deal Status",
            description="Determine deal status based on data availability",
            raw_sql="""
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN deal.CDB_cdi_file_nme IS NOT NULL THEN 'Complete'
                        ELSE 'Partial'
                    END AS deal_status
                FROM deal
            """,
            result_column_name="deal_status",
            group_level=GroupLevel.DEAL,
            created_by="test_system",
            is_active=True,
            approved_by="test_system",
            approval_date=datetime.now()
        )
    ]
    
    for calc in calculations:
        config_db_session.add(calc)
    config_db_session.commit()
    
    return calculations


@pytest.fixture 
def sample_report_deal_scope(config_db_session, sample_user_calculations, sample_system_calculations) -> Report:
    """Create a sample deal-scoped report for testing"""
    report = Report(
        name="Test Deal Report",
        description="A test report at deal scope",
        scope="DEAL",
        created_by="test_user",
        is_active=True,
        column_preferences={
            "columns": [
                {
                    "column_id": "static_deal.dl_nbr",
                    "display_name": "Deal Number", 
                    "is_visible": True,
                    "display_order": 0,
                    "format_type": "number"
                },
                {
                    "column_id": f"user.{sample_user_calculations[0].source_field}",
                    "display_name": "Total Balance",
                    "is_visible": True,
                    "display_order": 1,
                    "format_type": "currency"
                },
                {
                    "column_id": f"system.{sample_system_calculations[0].result_column_name}",
                    "display_name": "Issuer Type",
                    "is_visible": True,
                    "display_order": 2,
                    "format_type": "text"
                }
            ]
        }
    )
    
    config_db_session.add(report)
    config_db_session.flush()
    
    # Add deals
    deal1 = ReportDeal(report_id=report.id, dl_nbr=1001)
    deal2 = ReportDeal(report_id=report.id, dl_nbr=1002)
    config_db_session.add(deal1)
    config_db_session.add(deal2)
    config_db_session.flush()
    
    # Add calculations
    calc1 = ReportCalculation(
        report_id=report.id,
        calculation_id="static_deal.dl_nbr", 
        calculation_type="static",
        display_order=0,
        display_name="Deal Number"
    )
    calc2 = ReportCalculation(
        report_id=report.id,
        calculation_id=f"user.{sample_user_calculations[0].source_field}",
        calculation_type="user",
        display_order=1,
        display_name="Total Balance"
    )
    calc3 = ReportCalculation(
        report_id=report.id,
        calculation_id=f"system.{sample_system_calculations[0].result_column_name}",
        calculation_type="system", 
        display_order=2,
        display_name="Issuer Type"
    )
    
    config_db_session.add(calc1)
    config_db_session.add(calc2)
    config_db_session.add(calc3)
    config_db_session.commit()
    
    return report


@pytest.fixture
def sample_report_tranche_scope(config_db_session, sample_user_calculations, sample_system_calculations) -> Report:
    """Create a sample tranche-scoped report for testing"""
    report = Report(
        name="Test Tranche Report", 
        description="A test report at tranche scope",
        scope="TRANCHE",
        created_by="test_user",
        is_active=True,
        column_preferences={
            "columns": [
                {
                    "column_id": "static_deal.dl_nbr",
                    "display_name": "Deal Number",
                    "is_visible": True,
                    "display_order": 0,
                    "format_type": "number"
                },
                {
                    "column_id": "static_tranche.tr_id",
                    "display_name": "Tranche ID",
                    "is_visible": True,
                    "display_order": 1,
                    "format_type": "text"
                },
                {
                    "column_id": f"user.{sample_user_calculations[2].source_field}",  # Tranche-level calc
                    "display_name": "Tranche Balance",
                    "is_visible": True,
                    "display_order": 2,
                    "format_type": "currency"
                }
            ]
        }
    )
    
    config_db_session.add(report)
    config_db_session.flush()
    
    # Add deal with specific tranches
    deal = ReportDeal(report_id=report.id, dl_nbr=1001)
    config_db_session.add(deal)
    config_db_session.flush()
    
    # Add specific tranches
    tranche_a = ReportTranche(report_deal_id=deal.id, dl_nbr=1001, tr_id="A")
    tranche_b = ReportTranche(report_deal_id=deal.id, dl_nbr=1001, tr_id="B")
    config_db_session.add(tranche_a)
    config_db_session.add(tranche_b)
    
    # Add calculations
    calc1 = ReportCalculation(
        report_id=report.id,
        calculation_id="static_deal.dl_nbr",
        calculation_type="static",
        display_order=0,
        display_name="Deal Number"
    )
    calc2 = ReportCalculation(
        report_id=report.id,
        calculation_id="static_tranche.tr_id",
        calculation_type="static",
        display_order=1,
        display_name="Tranche ID"
    )
    calc3 = ReportCalculation(
        report_id=report.id,
        calculation_id=f"user.{sample_user_calculations[2].source_field}",
        calculation_type="user",
        display_order=2,
        display_name="Tranche Balance"
    )
    
    config_db_session.add(calc1)
    config_db_session.add(calc2)
    config_db_session.add(calc3)
    config_db_session.commit()
    
    return report


# ===== UTILITY FIXTURES =====

@pytest.fixture
def api_headers():
    """Standard API headers for testing"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@pytest.fixture
def test_cycle_code():
    """Standard test cycle code"""
    return 202404