"""
Phase 1 Test Validation Script

Run this script to validate that the QueryBuilder refactor is working correctly
and that all existing functionality is preserved.

Usage:
    python test_phase1.py

This script will:
1. Test that the new QueryBuilder produces valid SQL
2. Verify that preview and execution use identical queries  
3. Confirm backward compatibility with existing API
4. Test various query scenarios
"""

import sys
import os
from typing import List, Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))


def test_query_builder():
    """Test the new QueryBuilder directly."""
    print("🧪 Testing QueryBuilder directly...")

    try:
        from app.core.database import get_dw_db, get_db
        from app.query import (
            QueryBuilder,
            QueryParameters,
            CalculationDefinition,
            DealTrancheFilter,
            AggregationLevel,
            FieldType,
        )

        # Get database sessions
        dw_db = next(get_dw_db())

        # Create QueryBuilder
        builder = QueryBuilder(dw_db)

        # Test 1: System fields availability
        system_fields = builder.get_available_system_fields()
        print(f"✅ Found {len(system_fields)} system fields")
        for field in system_fields[:3]:  # Show first 3
            print(f"   - {field.name} ({field.table_name}.{field.column_name})")

        # Test 2: Available tables
        tables = builder.get_available_tables()
        print(f"✅ Found {len(tables)} available tables: {tables}")

        # Test 3: Build a simple query with system fields only
        deal_filters = [DealTrancheFilter(deal_number=1001, tranche_ids=None)]
        system_field_calc = CalculationDefinition(
            id=1,
            name="Deal Number",
            field_type=FieldType.SYSTEM,
            source_field=system_fields[0],  # Use first system field
        )

        params = QueryParameters(
            deal_tranche_filters=deal_filters,
            cycle_code=202404,
            calculations=[system_field_calc],
            aggregation_level=AggregationLevel.DEAL,
        )

        # Build query
        query = builder.build_query(params)
        print("✅ Successfully built query with system fields")

        # Test 4: Build preview
        preview = builder.build_preview(params)
        print(f"✅ Successfully built preview with {len(preview.query_result.columns)} columns")
        print(f"   SQL length: {len(preview.query_result.sql)} characters")

        print("✅ QueryBuilder tests passed!")
        return True

    except Exception as e:
        print(f"❌ QueryBuilder test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query_engine_compatibility():
    """Test that QueryEngine uses the new clean API."""
    print("\n🧪 Testing QueryEngine clean API...")

    try:
        from app.core.database import get_dw_db, get_db
        from app.query import QueryEngine

        # Get database sessions
        dw_db = next(get_dw_db())
        config_db = next(get_db())

        # Create QueryEngine (should use new QueryBuilder internally)
        engine = QueryEngine(dw_db, config_db)

        # Test 1: Clean API methods
        clean_methods = [
            "build_query",
            "get_preview",
            "execute_query",
            "execute_and_process",
            "get_available_system_fields",
            "get_available_tables",
        ]

        for method_name in clean_methods:
            if hasattr(engine, method_name):
                print(f"✅ Clean method {method_name} available")
            else:
                print(f"❌ Clean method {method_name} missing")
                return False

        # Test 2: Get available system fields
        system_fields = engine.get_available_system_fields()
        print(f"✅ Clean API returned {len(system_fields)} system fields")

        # Test 3: Get available tables
        tables = engine.get_available_tables()
        print(f"✅ Clean API returned {len(tables)} tables: {tables}")

        # Test 4: Test query building with clean API
        from app.query import (
            QueryParameters,
            CalculationDefinition,
            DealTrancheFilter,
            AggregationLevel,
            FieldType,
        )

        deal_filters = [DealTrancheFilter(deal_number=1001, tranche_ids=None)]
        system_field_calc = CalculationDefinition(
            id=1, name="Test Field", field_type=FieldType.SYSTEM, source_field=system_fields[0]
        )

        params = QueryParameters(
            deal_tranche_filters=deal_filters,
            cycle_code=202404,
            calculations=[system_field_calc],
            aggregation_level=AggregationLevel.DEAL,
        )

        # Test query building
        query = engine.build_query(params)
        print("✅ Successfully built query using clean API")

        # Test preview
        preview = engine.get_preview(params)
        print(f"✅ Successfully built preview using clean API")

        print("✅ QueryEngine clean API tests passed!")
        return True

    except Exception as e:
        print(f"❌ QueryEngine clean API test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_identical_preview_execution():
    """Test that preview and execution generate identical SQL."""
    print("\n🧪 Testing identical preview/execution SQL generation...")

    try:
        from app.core.database import get_dw_db, get_db
        from app.query import QueryEngine
        from app.query import (
            QueryParameters,
            CalculationDefinition,
            DealTrancheFilter,
            AggregationLevel,
            FieldType,
        )

        # Get database sessions
        dw_db = next(get_dw_db())
        config_db = next(get_db())

        # Create QueryEngine
        engine = QueryEngine(dw_db, config_db)

        # Create test parameters
        system_fields = engine.get_available_system_fields()
        deal_filters = [DealTrancheFilter(deal_number=1001, tranche_ids=["A", "B"])]

        params = QueryParameters(
            deal_tranche_filters=deal_filters,
            cycle_code=202404,
            calculations=[
                CalculationDefinition(
                    id=1,
                    name="Test Field",
                    field_type=FieldType.SYSTEM,
                    source_field=system_fields[0],
                )
            ],
            aggregation_level=AggregationLevel.TRANCHE,
        )

        # Build query for execution
        execution_query = engine.build_query(params)
        execution_sql = engine.query_builder._compile_query_to_sql(execution_query)

        # Build preview
        preview_result = engine.get_preview(params)
        preview_sql = preview_result["sql"]

        # Compare SQL (should be identical)
        if execution_sql == preview_sql:
            print("✅ Preview and execution SQL are identical")
            print(f"   SQL length: {len(execution_sql)} characters")
            return True
        else:
            print("❌ Preview and execution SQL differ!")
            print(
                "Execution SQL:",
                execution_sql[:200] + "..." if len(execution_sql) > 200 else execution_sql,
            )
            print(
                "Preview SQL:", preview_sql[:200] + "..." if len(preview_sql) > 200 else preview_sql
            )
            return False

    except Exception as e:
        print(f"❌ Identical SQL test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 1 validation tests."""
    print("🚀 Starting Phase 1 Validation Tests")
    print("=" * 50)

    test_results = []

    # Run tests
    test_results.append(test_query_builder())
    test_results.append(test_query_engine_compatibility())
    test_results.append(test_identical_preview_execution())

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(test_results)
    total = len(test_results)

    if passed == total:
        print(f"✅ All {total} tests passed! Phase 1 refactor is working correctly.")
        print("\n🎉 Ready to proceed with manual testing via the frontend!")
        print("\nNext steps:")
        print("1. Start your FastAPI application")
        print("2. Test existing report functionality through the UI")
        print("3. Verify that preview SQL matches execution behavior")
        print("4. Confirm all existing endpoints work as expected")
    else:
        print(f"❌ {total - passed} out of {total} tests failed.")
        print("Please fix the issues before proceeding to manual testing.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
