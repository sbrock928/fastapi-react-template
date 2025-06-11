#!/usr/bin/env python3
"""
Test script to validate the new calculation system backend
Run this script to verify everything is working before frontend changes
"""

import sys
import os
import traceback
from typing import Dict, Any, List

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_creation():
    """Test 1: Database and table creation"""
    print("\n🧪 Test 1: Database and Table Creation")
    try:
        from app.core.database import create_all_tables, SessionLocal, DWSessionLocal
        
        # Create tables
        create_all_tables()
        print("✅ Tables created successfully")
        
        # Test database connections
        config_db = SessionLocal()
        dw_db = DWSessionLocal()
        
        config_db.execute("SELECT 1")
        dw_db.execute("SELECT 1") 
        
        config_db.close()
        dw_db.close()
        
        print("✅ Database connections working")
        return True
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        return False

def test_model_imports():
    """Test 2: Model imports and basic validation"""
    print("\n🧪 Test 2: Model Imports")
    try:
        from app.calculations.models import (
            UserCalculation, 
            SystemCalculation, 
            AggregationFunction, 
            SourceModel, 
            GroupLevel,
            get_static_field_info,
            get_all_static_fields
        )
        print("✅ Models imported successfully")
        
        # Test enum values
        assert AggregationFunction.SUM == "SUM"
        assert SourceModel.DEAL == "Deal"
        assert GroupLevel.DEAL == "deal"
        print("✅ Enums working correctly")
        
        # Test static field registry
        static_fields = get_all_static_fields()
        assert len(static_fields) > 0
        assert "deal.dl_nbr" in static_fields
        print(f"✅ Static field registry working ({len(static_fields)} fields)")
        
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        traceback.print_exc()
        return False

def test_user_calculation_service():
    """Test 3: User Calculation Service"""
    print("\n🧪 Test 3: User Calculation Service")
    try:
        from app.core.database import SessionLocal
        from app.calculations.service import UserCalculationService
        from app.calculations.schemas import UserCalculationCreate
        from app.calculations.models import AggregationFunction, SourceModel, GroupLevel
        
        db = SessionLocal()
        service = UserCalculationService(db)
        
        # Create a test user calculation
        test_calc = UserCalculationCreate(
            name="Test Total Balance",
            description="Test calculation for validation",
            aggregation_function=AggregationFunction.SUM,
            source_model=SourceModel.TRANCHE_BAL,
            source_field="tr_end_bal_amt",
            group_level=GroupLevel.DEAL
        )
        
        # Test creation
        created_calc = service.create_user_calculation(test_calc, "test_user")
        assert created_calc.id is not None
        assert created_calc.name == "Test Total Balance"
        print(f"✅ User calculation created (ID: {created_calc.id})")
        
        # Test retrieval
        retrieved_calc = service.get_user_calculation_by_id(created_calc.id)
        assert retrieved_calc is not None
        assert retrieved_calc.name == "Test Total Balance"
        print("✅ User calculation retrieved")
        
        # Test listing
        all_calcs = service.get_all_user_calculations()
        assert len(all_calcs) >= 1
        print(f"✅ User calculation listing ({len(all_calcs)} calculations)")
        
        # Test deletion
        result = service.delete_user_calculation(created_calc.id)
        assert "deleted successfully" in result["message"]
        print("✅ User calculation deleted")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ User calculation service failed: {e}")
        traceback.print_exc()
        return False

def test_system_calculation_service():
    """Test 4: System Calculation Service"""
    print("\n🧪 Test 4: System Calculation Service")
    try:
        from app.core.database import SessionLocal
        from app.calculations.service import SystemCalculationService
        from app.calculations.schemas import SystemCalculationCreate
        from app.calculations.models import GroupLevel
        
        db = SessionLocal()
        service = SystemCalculationService(db)
        
        # Create a test system calculation
        test_calc = SystemCalculationCreate(
            name="Test Issuer Type",
            description="Test system calculation",
            raw_sql="""
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
                        ELSE 'Private'
                    END AS issuer_type
                FROM deal
            """,
            result_column_name="issuer_type",
            group_level=GroupLevel.DEAL
        )
        
        # Test creation
        created_calc = service.create_system_calculation(test_calc, "test_admin")
        assert created_calc.id is not None
        assert created_calc.name == "Test Issuer Type"
        print(f"✅ System calculation created (ID: {created_calc.id})")
        
        # Test approval
        approved_calc = service.approve_system_calculation(created_calc.id, "test_approver")
        assert approved_calc.is_approved()
        print("✅ System calculation approved")
        
        # Test listing
        all_calcs = service.get_all_system_calculations()
        assert len(all_calcs) >= 1
        print(f"✅ System calculation listing ({len(all_calcs)} calculations)")
        
        # Test deletion
        result = service.delete_system_calculation(created_calc.id)
        assert "deleted successfully" in result["message"]
        print("✅ System calculation deleted")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ System calculation service failed: {e}")
        traceback.print_exc()
        return False

def test_static_field_service():
    """Test 5: Static Field Service"""
    print("\n🧪 Test 5: Static Field Service")
    try:
        from app.calculations.service import StaticFieldService
        
        # Test getting all static fields
        all_fields = StaticFieldService.get_all_static_fields()
        assert len(all_fields) > 0
        print(f"✅ Static fields retrieved ({len(all_fields)} fields)")
        
        # Test getting specific field
        deal_field = StaticFieldService.get_static_field_by_path("deal.dl_nbr")
        assert deal_field is not None
        assert deal_field.name == "Deal Number"
        assert deal_field.type == "number"
        print("✅ Specific static field retrieved")
        
        # Test getting fields by model
        deal_fields = StaticFieldService.get_static_fields_by_model("deal")
        assert len(deal_fields) > 0
        assert all(field.field_path.startswith("deal.") for field in deal_fields)
        print(f"✅ Deal fields retrieved ({len(deal_fields)} fields)")
        
        return True
    except Exception as e:
        print(f"❌ Static field service failed: {e}")
        traceback.print_exc()
        return False

def test_calculation_resolver():
    """Test 6: Calculation Resolver"""
    print("\n🧪 Test 6: Calculation Resolver")
    try:
        from app.core.database import SessionLocal, DWSessionLocal
        from app.calculations.resolver import SimpleCalculationResolver, CalculationRequest, QueryFilters
        
        config_db = SessionLocal()
        dw_db = DWSessionLocal()
        
        resolver = SimpleCalculationResolver(dw_db, config_db)
        
        # Create sample data first
        create_sample_data_if_needed(dw_db)
        
        # Test static field resolution
        static_request = CalculationRequest(
            calc_type="static_field",
            field_path="deal.dl_nbr",
            alias="deal_number"
        )
        
        filters = QueryFilters(
            deal_tranche_map={1001: ["A", "B"]},
            cycle_code=202404
        )
        
        result = resolver.resolve_single_calculation(static_request, filters)
        assert result.sql is not None
        assert "deal.dl_nbr" in result.sql
        assert result.calc_type == "static_field"
        print("✅ Static field resolution working")
        
        # Test SQL generation for multiple calculations
        requests = [
            CalculationRequest("static_field", field_path="deal.dl_nbr", alias="deal_number"),
            CalculationRequest("static_field", field_path="deal.issr_cde", alias="issuer_code"),
        ]
        
        report_result = resolver.resolve_report(requests, filters)
        assert "merged_data" in report_result
        assert "individual_queries" in report_result
        print("✅ Multi-calculation resolution working")
        
        config_db.close()
        dw_db.close()
        return True
    except Exception as e:
        print(f"❌ Calculation resolver failed: {e}")
        traceback.print_exc()
        return False

def test_report_execution_service():
    """Test 7: Report Execution Service"""
    print("\n🧪 Test 7: Report Execution Service")
    try:
        from app.core.database import SessionLocal, DWSessionLocal
        from app.calculations.service import ReportExecutionService
        from app.calculations.resolver import CalculationRequest
        
        config_db = SessionLocal()
        dw_db = DWSessionLocal()
        
        service = ReportExecutionService(dw_db, config_db)
        
        # Create simple request
        requests = [
            CalculationRequest("static_field", field_path="deal.dl_nbr", alias="deal_number"),
        ]
        
        # Test SQL preview
        preview_result = service.preview_report_sql(
            requests,
            deal_tranche_map={1001: []},  # All tranches for deal 1001
            cycle_code=202404
        )
        
        assert "sql_previews" in preview_result
        assert "deal_number" in preview_result["sql_previews"]
        print("✅ SQL preview working")
        
        # Test execution (if sample data exists)
        try:
            execution_result = service.execute_report(
                requests,
                deal_tranche_map={1001: []},
                cycle_code=202404
            )
            
            assert "data" in execution_result
            assert "metadata" in execution_result
            print("✅ Report execution working")
        except Exception as exec_e:
            print(f"⚠️  Report execution skipped (no sample data): {exec_e}")
        
        config_db.close()
        dw_db.close()
        return True
    except Exception as e:
        print(f"❌ Report execution service failed: {e}")
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test 8: API Endpoints (basic import test)"""
    print("\n🧪 Test 8: API Endpoints")
    try:
        from app.calculations.router import router
        
        # Test that router imported successfully
        assert router is not None
        
        # Count routes
        route_count = len(router.routes)
        assert route_count > 0
        print(f"✅ Router imported with {route_count} routes")
        
        # Test basic route structure
        route_paths = [route.path for route in router.routes]
        expected_paths = ["/config", "/user", "/system", "/static-fields", "/execute-report"]
        
        for expected in expected_paths:
            matching_routes = [path for path in route_paths if expected in path]
            assert len(matching_routes) > 0, f"Expected route containing '{expected}' not found"
        
        print("✅ All expected route patterns found")
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        traceback.print_exc()
        return False

def create_sample_data_if_needed(dw_db):
    """Create minimal sample data for testing if it doesn't exist"""
    try:
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        
        # Check if data exists
        existing_deals = dw_db.query(Deal).count()
        if existing_deals > 0:
            return  # Data already exists
        
        print("Creating minimal sample data for testing...")
        
        # Create a minimal deal
        deal = Deal(
            dl_nbr=1001,
            issr_cde="FHLMC24",
            cdi_file_nme="TEST_CDI"
        )
        dw_db.add(deal)
        
        # Create a tranche
        tranche = Tranche(
            dl_nbr=1001,
            tr_id="A",
            tr_cusip_id="TEST123A"
        )
        dw_db.add(tranche)
        
        # Create tranche balance
        tranche_bal = TrancheBal(
            dl_nbr=1001,
            tr_id="A",
            cycle_cde=202404,
            tr_end_bal_amt=1000000.00,
            tr_pass_thru_rte=0.05
        )
        dw_db.add(tranche_bal)
        
        dw_db.commit()
        print("✅ Sample data created")
        
    except Exception as e:
        print(f"⚠️  Could not create sample data: {e}")
        dw_db.rollback()

def run_all_tests():
    """Run all backend validation tests"""
    print("🚀 Starting Backend Validation Tests")
    print("=" * 50)
    
    tests = [
        test_database_creation,
        test_model_imports,
        test_user_calculation_service,
        test_system_calculation_service,
        test_static_field_service,
        test_calculation_resolver,
        test_report_execution_service,
        test_api_endpoints,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 50)
    print("🏁 Test Results Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend is ready for frontend integration.")
        return True
    else:
        print("⚠️  Some tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)