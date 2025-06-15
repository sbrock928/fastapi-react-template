"""
API tests for the calculations module.
Tests user calculations, system calculations, and static fields functionality.
"""

import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient


class TestUserCalculationsCRUD:
    """Test user calculations CRUD operations"""

    def test_get_all_user_calculations(self, client: TestClient, sample_user_calculations):
        """Test getting all user calculations via unified endpoint"""
        response = client.get("/api/calculations")
        assert response.status_code == 200
        
        result = response.json()
        assert "user_calculations" in result
        assert "system_calculations" in result
        
        calculations = result["user_calculations"]
        assert len(calculations) == 3
        
        for calc in calculations:
            assert "id" in calc
            assert "name" in calc
            assert "aggregation_function" in calc
            assert "source_model" in calc
            assert "source_field" in calc
            assert "group_level" in calc

    def test_get_user_calculation_by_id(self, client: TestClient, sample_user_calculations):
        """Test getting a specific user calculation by ID"""
        calc_id = sample_user_calculations[0].id
        
        response = client.get(f"/api/calculations/user/{calc_id}")
        assert response.status_code == 200
        
        calc = response.json()
        assert calc["id"] == calc_id
        assert calc["name"] == "Total Balance"
        assert calc["aggregation_function"] == "SUM"
        assert calc["source_model"] == "TrancheBal"

    def test_create_user_calculation(self, client: TestClient, api_headers):
        """Test creating a new user calculation"""
        calc_data = {
            "name": "Interest Distribution",
            "description": "Sum of interest distributions",
            "aggregation_function": "SUM",
            "source_model": "TrancheBal",
            "source_field": "tr_int_dstrb_amt",
            "group_level": "deal",
            "created_by": "test_user"
        }
        
        response = client.post("/api/calculations/user", json=calc_data, headers=api_headers)
        assert response.status_code == 201
        
        created_calc = response.json()
        assert created_calc["name"] == "Interest Distribution"
        assert created_calc["aggregation_function"] == "SUM"
        assert created_calc["source_field"] == "tr_int_dstrb_amt"
        assert created_calc["group_level"] == "deal"

    def test_create_weighted_average_calculation(self, client: TestClient, api_headers):
        """Test creating a weighted average calculation"""
        calc_data = {
            "name": "Weighted Average Coupon",
            "description": "WAC calculation",
            "aggregation_function": "WEIGHTED_AVG",
            "source_model": "TrancheBal",
            "source_field": "tr_pass_thru_rte",
            "weight_field": "tr_end_bal_amt",
            "group_level": "deal",
            "created_by": "test_user"
        }
        
        response = client.post("/api/calculations/user", json=calc_data, headers=api_headers)
        assert response.status_code == 201
        
        created_calc = response.json()
        assert created_calc["aggregation_function"] == "WEIGHTED_AVG"
        assert created_calc["weight_field"] == "tr_end_bal_amt"

    def test_create_user_calculation_validation_errors(self, client: TestClient, api_headers):
        """Test validation errors when creating user calculations"""
        # Missing required fields
        response = client.post("/api/calculations/user", json={
            "name": "Invalid Calc"
        }, headers=api_headers)
        assert response.status_code == 422

        # Invalid aggregation function
        response = client.post("/api/calculations/user", json={
            "name": "Invalid Calc",
            "aggregation_function": "INVALID",
            "source_model": "TrancheBal",
            "source_field": "tr_end_bal_amt",
            "group_level": "deal",
            "created_by": "test_user"
        }, headers=api_headers)
        assert response.status_code == 422

    def test_update_user_calculation(self, client: TestClient, api_headers, sample_user_calculations):
        """Test updating an existing user calculation"""
        calc_id = sample_user_calculations[0].id
        
        update_data = {
            "name": "Updated Total Balance",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/calculations/user/{calc_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        
        updated_calc = response.json()
        assert updated_calc["name"] == "Updated Total Balance"
        assert updated_calc["description"] == "Updated description"

    def test_delete_user_calculation(self, client: TestClient, sample_user_calculations):
        """Test deleting a user calculation"""
        calc_id = sample_user_calculations[0].id
        
        response = client.delete(f"/api/calculations/user/{calc_id}")
        assert response.status_code == 200
        
        # Verify calculation is no longer accessible
        response = client.get(f"/api/calculations/user/{calc_id}")
        assert response.status_code == 404

    def test_approve_user_calculation(self, client: TestClient, api_headers, config_db_session):
        """Test approving a user calculation"""
        from app.calculations.models import UserCalculation, AggregationFunction, SourceModel, GroupLevel
        
        # Create an unapproved calculation
        calc = UserCalculation(
            name="Unapproved Calc",
            description="Test calculation",
            aggregation_function=AggregationFunction.SUM,
            source_model=SourceModel.TRANCHE_BAL,
            source_field="tr_end_bal_amt",
            group_level=GroupLevel.DEAL,
            created_by="test_user",
            is_active=True
        )
        config_db_session.add(calc)
        config_db_session.commit()
        
        response = client.post(f"/api/calculations/user/{calc.id}/approve", 
                             json={"approved_by": "test_approver"}, headers=api_headers)
        assert response.status_code == 200
        
        approved_calc = response.json()
        assert approved_calc["approved_by"] == "test_approver"


class TestSystemCalculationsCRUD:
    """Test system calculations CRUD operations"""

    def test_get_all_system_calculations(self, client: TestClient, sample_system_calculations):
        """Test getting all system calculations via unified endpoint"""
        response = client.get("/api/calculations")
        assert response.status_code == 200
        
        result = response.json()
        assert "user_calculations" in result
        assert "system_calculations" in result
        
        calculations = result["system_calculations"]
        assert len(calculations) == 2
        
        for calc in calculations:
            assert "id" in calc
            assert "name" in calc
            assert "raw_sql" in calc
            assert "result_column_name" in calc
            assert "group_level" in calc

    def test_get_system_calculation_by_id(self, client: TestClient, sample_system_calculations):
        """Test getting a specific system calculation by ID"""
        calc_id = sample_system_calculations[0].id
        
        response = client.get(f"/api/calculations/system/{calc_id}")
        assert response.status_code == 200
        
        calc = response.json()
        assert calc["id"] == calc_id
        assert calc["name"] == "Issuer Type"
        assert calc["result_column_name"] == "issuer_type"
        assert "SELECT" in calc["raw_sql"].upper()

    def test_create_system_calculation(self, client: TestClient, api_headers):
        """Test creating a new system calculation"""
        calc_data = {
            "name": "File Count",
            "description": "Count of files per deal",
            "raw_sql": """
                SELECT 
                    deal.dl_nbr,
                    CASE 
                        WHEN deal.cdi_file_nme IS NOT NULL AND deal.CDB_cdi_file_nme IS NOT NULL THEN 2
                        WHEN deal.cdi_file_nme IS NOT NULL THEN 1
                        ELSE 0
                    END AS file_count
                FROM deal
            """,
            "result_column_name": "file_count",
            "group_level": "deal",
            "created_by": "test_user"
        }
        
        response = client.post("/api/calculations/system", json=calc_data, headers=api_headers)
        assert response.status_code == 201
        
        created_calc = response.json()
        assert created_calc["name"] == "File Count"
        assert created_calc["result_column_name"] == "file_count"
        assert created_calc["approved_by"] == "system_auto_approval"  # Auto-approved

    def test_validate_system_sql(self, client: TestClient, api_headers):
        """Test SQL validation for system calculations"""
        # Valid SQL
        valid_sql_data = {
            "sql_text": """
                SELECT 
                    deal.dl_nbr,
                    deal.issr_cde AS issuer_code
                FROM deal
            """,
            "group_level": "deal",
            "result_column_name": "issuer_code"
        }
        
        response = client.post("/api/calculations/validate-system-sql", json=valid_sql_data, headers=api_headers)
        assert response.status_code == 200
        
        validation = response.json()["validation_result"]
        assert validation["is_valid"] == True
        assert len(validation["errors"]) == 0

        # Invalid SQL - missing required table
        invalid_sql_data = {
            "sql_text": "SELECT 1 as test",
            "group_level": "deal",
            "result_column_name": "test"
        }
        
        response = client.post("/api/calculations/validate-system-sql", json=invalid_sql_data, headers=api_headers)
        assert response.status_code == 200
        
        validation = response.json()["validation_result"]
        assert validation["is_valid"] == False
        assert len(validation["errors"]) > 0

    def test_system_calculation_validation_errors(self, client: TestClient, api_headers):
        """Test validation errors for system calculations"""
        # Invalid result column name
        calc_data = {
            "name": "Invalid Calc",
            "raw_sql": "SELECT deal.dl_nbr FROM deal",
            "result_column_name": "123invalid",  # Cannot start with number
            "group_level": "deal",
            "created_by": "test_user"
        }
        
        response = client.post("/api/calculations/system", json=calc_data, headers=api_headers)
        assert response.status_code == 422

    def test_update_system_calculation(self, client: TestClient, api_headers, sample_system_calculations):
        """Test updating an existing system calculation"""
        calc_id = sample_system_calculations[0].id
        
        update_data = {
            "name": "Updated Issuer Type",
            "description": "Updated categorization"
        }
        
        response = client.patch(f"/api/calculations/system/{calc_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        
        updated_calc = response.json()
        assert updated_calc["name"] == "Updated Issuer Type"
        assert updated_calc["description"] == "Updated categorization"

    def test_delete_system_calculation(self, client: TestClient, sample_system_calculations):
        """Test deleting a system calculation"""
        calc_id = sample_system_calculations[0].id
        
        response = client.delete(f"/api/calculations/system/{calc_id}")
        assert response.status_code == 200


class TestStaticFields:
    """Test static fields functionality"""

    def test_get_all_static_fields(self, client: TestClient):
        """Test getting all static fields"""
        response = client.get("/api/calculations/static-fields")
        assert response.status_code == 200
        
        fields = response.json()
        assert len(fields) > 0
        
        for field in fields:
            assert "field_path" in field
            assert "name" in field
            assert "type" in field
            assert "required_models" in field

    def test_get_static_fields_by_model(self, client: TestClient):
        """Test getting static fields filtered by model"""
        response = client.get("/api/calculations/static-fields", params={"model": "Deal"})
        assert response.status_code == 200
        
        fields = response.json()
        assert len(fields) > 0
        
        # All fields should be Deal-related
        for field in fields:
            assert "Deal" in field["required_models"]

    def test_get_calculation_config(self, client: TestClient):
        """Test getting calculation configuration for UI"""
        response = client.get("/api/calculations/config")
        assert response.status_code == 200
        
        config = response.json()
        assert "aggregation_functions" in config
        assert "source_models" in config
        assert "group_levels" in config
        assert "static_fields" in config
        
        # Check structure
        assert len(config["aggregation_functions"]) > 0
        assert len(config["source_models"]) > 0
        assert len(config["group_levels"]) > 0


class TestCalculationUsage:
    """Test calculation usage tracking"""

    def test_get_user_calculation_usage(self, client: TestClient, sample_user_calculations, sample_report_deal_scope):
        """Test getting usage information for user calculations"""
        calc_id = sample_user_calculations[0].id
        
        response = client.get(f"/api/calculations/user/{calc_id}/usage")
        assert response.status_code == 200
        
        usage = response.json()
        assert "calculation_id" in usage
        assert "is_in_use" in usage
        assert "report_count" in usage
        assert "reports" in usage
        
        # Should show usage from sample report
        assert usage["is_in_use"] == True
        assert usage["report_count"] > 0

    def test_get_system_calculation_usage(self, client: TestClient, sample_system_calculations, sample_report_deal_scope):
        """Test getting usage information for system calculations"""
        calc_id = sample_system_calculations[0].id
        
        response = client.get(f"/api/calculations/system/{calc_id}/usage")
        assert response.status_code == 200
        
        usage = response.json()
        assert "calculation_id" in usage
        assert "is_in_use" in usage
        assert "report_count" in usage

    def test_get_calculation_usage_by_new_id_format(self, client: TestClient, sample_user_calculations):
        """Test getting usage by new calculation_id format"""
        user_calc = sample_user_calculations[0]
        calc_id = f"user.{user_calc.source_field}"
        
        response = client.get(f"/api/calculations/usage/{calc_id}")
        assert response.status_code == 200
        
        usage = response.json()
        assert usage["calculation_id"] == calc_id

    def test_get_calculation_counts(self, client: TestClient, sample_user_calculations, sample_system_calculations):
        """Test getting calculation count statistics"""
        response = client.get("/api/calculations/stats/counts")
        assert response.status_code == 200
        
        stats = response.json()
        assert "counts" in stats
        assert "breakdown" in stats
        
        counts = stats["counts"]
        assert "user_calculations" in counts
        assert "system_calculations" in counts
        assert "total" in counts


class TestCalculationExecution:
    """Test calculation execution functionality"""

    def test_execute_report_with_mixed_calculations(self, client: TestClient, api_headers, 
                                                  sample_user_calculations, sample_system_calculations,
                                                  sample_tranche_balances, test_cycle_code):
        """Test executing a report with mixed calculation types"""
        request_data = {
            "calculation_requests": [
                {
                    "calc_type": "static_field",
                    "field_path": "deal.dl_nbr",
                    "alias": "deal_number"
                },
                {
                    "calc_type": "user_calculation",
                    "calc_id": sample_user_calculations[0].id,
                    "alias": "total_balance"
                },
                {
                    "calc_type": "system_calculation",
                    "calc_id": sample_system_calculations[0].id,
                    "alias": "issuer_type"
                }
            ],
            "deal_tranche_map": {
                "1001": ["A", "B"],
                "1002": []
            },
            "cycle_code": test_cycle_code
        }
        
        response = client.post("/api/calculations/execute-report", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        assert "data" in result
        assert "metadata" in result
        
        data = result["data"]
        assert len(data) > 0
        
        # Check that all calculation types are present
        first_row = data[0]
        assert "deal_number" in first_row
        assert "total_balance" in first_row
        assert "issuer_type" in first_row

    def test_preview_report_sql(self, client: TestClient, api_headers, sample_user_calculations, test_cycle_code):
        """Test previewing SQL for report execution"""
        request_data = {
            "calculation_requests": [
                {
                    "calc_type": "static_field",
                    "field_path": "deal.dl_nbr",
                    "alias": "deal_number"
                },
                {
                    "calc_type": "user_calculation",
                    "calc_id": sample_user_calculations[0].id,
                    "alias": "total_balance"
                }
            ],
            "deal_tranche_map": {"1001": ["A"]},
            "cycle_code": test_cycle_code
        }
        
        response = client.post("/api/calculations/preview-sql", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        preview = response.json()
        assert "sql_previews" in preview
        assert "parameters" in preview
        assert "summary" in preview
        
        sql_previews = preview["sql_previews"]
        assert "deal_number" in sql_previews
        assert "total_balance" in sql_previews
        
        # Each preview should contain SQL
        for calc_name, preview_data in sql_previews.items():
            assert "sql" in preview_data
            assert "calculation_type" in preview_data

    def test_preview_single_calculation(self, client: TestClient, api_headers, sample_user_calculations, test_cycle_code):
        """Test previewing SQL for a single calculation"""
        request_data = {
            "calculation_request": {
                "calc_type": "user_calculation",
                "calc_id": sample_user_calculations[0].id,
                "alias": "total_balance"
            },
            "deal_tranche_map": {"1001": ["A"]},
            "cycle_code": test_cycle_code
        }
        
        response = client.post("/api/calculations/preview-single", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        preview = response.json()
        assert "sql" in preview
        assert "calculation_type" in preview


class TestCalculationValidation:
    """Test calculation validation functionality"""

    def test_validate_user_calculation_source_field(self, client: TestClient, api_headers):
        """Test validating user calculation source field availability"""
        request_data = {"source_field": "tr_end_bal_amt"}
        
        response = client.post("/api/calculations/user/validate-source-field", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        validation = response.json()
        assert "is_available" in validation

    def test_validate_system_calculation_result_column(self, client: TestClient, api_headers):
        """Test validating system calculation result column availability"""
        request_data = {"result_column": "new_calculation_result"}
        
        response = client.post("/api/calculations/system/validate-result-column", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        validation = response.json()
        assert "is_available" in validation

    def test_get_user_calculation_by_source_field(self, client: TestClient, sample_user_calculations):
        """Test getting user calculation by source field (new ID format)"""
        source_field = sample_user_calculations[0].source_field
        
        response = client.get(f"/api/calculations/user/by-source-field/{source_field}")
        assert response.status_code == 200
        
        calc = response.json()
        assert calc["source_field"] == source_field

    def test_get_system_calculation_by_result_column(self, client: TestClient, sample_system_calculations):
        """Test getting system calculation by result column (new ID format)"""
        result_column = sample_system_calculations[0].result_column_name
        
        response = client.get(f"/api/calculations/system/by-result-column/{result_column}")
        assert response.status_code == 200
        
        calc = response.json()
        assert calc["result_column_name"] == result_column


class TestCalculationHealth:
    """Test calculation system health and status"""

    def test_calculation_system_health(self, client: TestClient):
        """Test calculation system health check"""
        response = client.get("/api/calculations/health")
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        assert "system" in health
        assert "features" in health
        
        # Should include expected features
        features = health["features"]
        assert "user_calculations" in features
        assert "system_calculations" in features
        assert "static_fields" in features

    def test_unified_calculations_endpoint(self, client: TestClient, sample_user_calculations, sample_system_calculations):
        """Test the unified calculations endpoint"""
        response = client.get("/api/calculations")
        assert response.status_code == 200
        
        result = response.json()
        assert "user_calculations" in result
        assert "system_calculations" in result
        assert "summary" in result
        
        # Should have our sample calculations
        assert len(result["user_calculations"]) == 3
        assert len(result["system_calculations"]) == 2