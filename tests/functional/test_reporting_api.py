"""
API tests for the reporting module.
Tests report CRUD operations, execution, and column preferences functionality.
"""

import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient


class TestReportCRUD:
    """Test report configuration CRUD operations"""

    def test_get_all_reports(self, client: TestClient, sample_report_deal_scope, sample_report_tranche_scope):
        """Test getting all reports"""
        response = client.get("/api/reports/")
        assert response.status_code == 200
        
        reports = response.json()
        assert len(reports) == 2
        
        # Check report structure
        for report in reports:
            assert "id" in report
            assert "name" in report
            assert "scope" in report
            assert "selected_deals" in report
            assert "selected_calculations" in report
            assert "column_preferences" in report

    def test_get_report_by_id(self, client: TestClient, sample_report_deal_scope):
        """Test getting a specific report by ID"""
        report_id = sample_report_deal_scope.id
        
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 200
        
        report = response.json()
        assert report["id"] == report_id
        assert report["name"] == "Test Deal Report"
        assert report["scope"] == "DEAL"
        assert len(report["selected_deals"]) == 2
        assert len(report["selected_calculations"]) == 3

    def test_get_nonexistent_report(self, client: TestClient):
        """Test getting a report that doesn't exist"""
        response = client.get("/api/reports/99999")
        assert response.status_code == 404

    def test_create_deal_report(self, client: TestClient, api_headers, sample_deals, sample_user_calculations):
        """Test creating a new deal-scoped report"""
        report_data = {
            "name": "New Deal Report",
            "description": "A new test report",
            "scope": "DEAL",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [
                {
                    "dl_nbr": 1001,
                    "selected_tranches": []
                }
            ],
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0,
                    "display_name": "Deal Number"
                },
                {
                    "calculation_id": f"user.{sample_user_calculations[0].source_field}",
                    "calculation_type": "user",
                    "display_order": 1,
                    "display_name": "Total Balance"
                }
            ],
            "column_preferences": {
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
                    }
                ]
            }
        }
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200
        
        created_report = response.json()
        assert created_report["name"] == "New Deal Report"
        assert created_report["scope"] == "DEAL"
        assert len(created_report["selected_deals"]) == 1
        assert len(created_report["selected_calculations"]) == 2
        assert created_report["column_preferences"] is not None

    def test_create_tranche_report(self, client: TestClient, api_headers, sample_deals, sample_user_calculations):
        """Test creating a new tranche-scoped report"""
        report_data = {
            "name": "New Tranche Report",
            "description": "A new tranche test report",
            "scope": "TRANCHE",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [
                {
                    "dl_nbr": 1001,
                    "selected_tranches": [
                        {"tr_id": "A", "dl_nbr": 1001},
                        {"tr_id": "B", "dl_nbr": 1001}
                    ]
                }
            ],
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0,
                    "display_name": "Deal Number"
                },
                {
                    "calculation_id": "static_tranche.tr_id",
                    "calculation_type": "static",
                    "display_order": 1,
                    "display_name": "Tranche ID"
                },
                {
                    "calculation_id": f"user.{sample_user_calculations[2].source_field}",  # Tranche-level calc
                    "calculation_type": "user",
                    "display_order": 2,
                    "display_name": "Tranche Balance"
                }
            ]
        }
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200
        
        created_report = response.json()
        assert created_report["name"] == "New Tranche Report"
        assert created_report["scope"] == "TRANCHE"
        assert len(created_report["selected_deals"]) == 1
        assert len(created_report["selected_deals"][0]["selected_tranches"]) == 2

    def test_create_report_validation_errors(self, client: TestClient, api_headers):
        """Test validation errors when creating reports"""
        # Empty name
        response = client.post("/api/reports/", json={
            "name": "",
            "scope": "DEAL",
            "selected_deals": [],
            "selected_calculations": []
        }, headers=api_headers)
        assert response.status_code == 422

        # No deals selected
        response = client.post("/api/reports/", json={
            "name": "Test Report",
            "scope": "DEAL",
            "selected_deals": [],
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0
                }
            ]
        }, headers=api_headers)
        assert response.status_code == 422

        # No calculations selected
        response = client.post("/api/reports/", json={
            "name": "Test Report",
            "scope": "DEAL",
            "selected_deals": [{"dl_nbr": 1001, "selected_tranches": []}],
            "selected_calculations": []
        }, headers=api_headers)
        assert response.status_code == 422

    def test_update_report(self, client: TestClient, api_headers, sample_report_deal_scope):
        """Test updating an existing report"""
        report_id = sample_report_deal_scope.id
        
        update_data = {
            "name": "Updated Deal Report",
            "description": "Updated description",
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0,
                    "display_name": "Deal Number"
                }
            ]
        }
        
        response = client.patch(f"/api/reports/{report_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        
        updated_report = response.json()
        assert updated_report["name"] == "Updated Deal Report"
        assert updated_report["description"] == "Updated description"
        assert len(updated_report["selected_calculations"]) == 1

    def test_delete_report(self, client: TestClient, sample_report_deal_scope):
        """Test deleting a report (soft delete)"""
        report_id = sample_report_deal_scope.id
        
        response = client.delete(f"/api/reports/{report_id}")
        assert response.status_code == 200
        
        # Verify report is no longer accessible
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 404


class TestReportExecution:
    """Test report execution functionality"""

    def test_run_deal_report(self, client: TestClient, api_headers, sample_report_deal_scope, 
                           sample_deals, sample_tranche_balances, test_cycle_code):
        """Test running a deal-scoped report"""
        report_id = sample_report_deal_scope.id
        
        request_data = {
            "cycle_code": test_cycle_code
        }
        
        response = client.post(f"/api/reports/run/{report_id}", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        assert "data" in result
        assert "columns" in result
        assert "total_rows" in result
        
        # Should have data for the selected deals
        assert len(result["data"]) > 0
        
        # Check column metadata
        columns = result["columns"]
        assert len(columns) > 0
        for col in columns:
            assert "field" in col
            assert "header" in col
            assert "format_type" in col
            assert "display_order" in col

    def test_run_tranche_report(self, client: TestClient, api_headers, sample_report_tranche_scope,
                              sample_deals, sample_tranche_balances, test_cycle_code):
        """Test running a tranche-scoped report"""
        report_id = sample_report_tranche_scope.id
        
        request_data = {
            "cycle_code": test_cycle_code
        }
        
        response = client.post(f"/api/reports/run/{report_id}", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        assert "data" in result
        assert "columns" in result
        
        # Should have data for selected tranches
        data = result["data"]
        assert len(data) > 0
        
        # Each row should have tranche information
        for row in data:
            assert "deal_number" in row or any("deal" in k.lower() for k in row.keys())
            assert "tranche_id" in row or any("tranche" in k.lower() for k in row.keys())

    def test_run_report_with_mixed_calculations(self, client: TestClient, api_headers, sample_deals,
                                              sample_user_calculations, sample_system_calculations,
                                              sample_tranche_balances, test_cycle_code, config_db_session):
        """Test running a report with mixed calculation types (user + system + static)"""
        # Create a report with all calculation types
        from app.reporting.models import Report, ReportDeal, ReportCalculation
        
        report = Report(
            name="Mixed Calculation Report",
            description="Report with user, system, and static calculations",
            scope="DEAL",
            created_by="test_user",
            is_active=True
        )
        
        config_db_session.add(report)
        config_db_session.flush()
        
        # Add deal
        deal = ReportDeal(report_id=report.id, dl_nbr=1001)
        config_db_session.add(deal)
        config_db_session.flush()
        
        # Add mixed calculations
        calculations = [
            ReportCalculation(
                report_id=report.id,
                calculation_id="static_deal.dl_nbr",
                calculation_type="static",
                display_order=0,
                display_name="Deal Number"
            ),
            ReportCalculation(
                report_id=report.id,
                calculation_id=f"user.{sample_user_calculations[0].source_field}",
                calculation_type="user",
                display_order=1,
                display_name="Total Balance"
            ),
            ReportCalculation(
                report_id=report.id,
                calculation_id=f"system.{sample_system_calculations[0].result_column_name}",
                calculation_type="system",
                display_order=2,
                display_name="Issuer Type"
            )
        ]
        
        for calc in calculations:
            config_db_session.add(calc)
        config_db_session.commit()
        
        # Run the report
        request_data = {"cycle_code": test_cycle_code}
        response = client.post(f"/api/reports/run/{report.id}", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        data = result["data"]
        assert len(data) > 0
        
        # Verify all calculation types are present in results
        first_row = data[0]
        # Should have static field (deal number)
        assert any("deal" in k.lower() and "number" in k.lower() for k in first_row.keys())
        # Should have user calculation result
        assert any("balance" in k.lower() for k in first_row.keys())
        # Should have system calculation result  
        assert any("issuer" in k.lower() or "type" in k.lower() for k in first_row.keys())

    def test_run_nonexistent_report(self, client: TestClient, api_headers, test_cycle_code):
        """Test running a report that doesn't exist"""
        request_data = {"cycle_code": test_cycle_code}
        response = client.post("/api/reports/run/99999", json=request_data, headers=api_headers)
        assert response.status_code == 404


class TestReportStructure:
    """Test report structure and preview functionality"""

    def test_get_report_structure(self, client: TestClient, sample_report_deal_scope):
        """Test getting report structure for skeleton mode"""
        report_id = sample_report_deal_scope.id
        
        response = client.get(f"/api/reports/{report_id}/structure")
        assert response.status_code == 200
        
        structure = response.json()
        assert structure["report_id"] == report_id
        assert structure["name"] == "Test Deal Report"
        assert structure["scope"] == "DEAL"
        assert "columns" in structure
        assert "deal_count" in structure
        assert "calculation_count" in structure
        
        # Check column structure
        columns = structure["columns"]
        assert len(columns) > 0
        for col in columns:
            assert "field" in col
            assert "header" in col
            assert "format_type" in col
            assert "display_order" in col

    def test_preview_report_sql(self, client: TestClient, sample_report_deal_scope, test_cycle_code):
        """Test previewing SQL for a report"""
        report_id = sample_report_deal_scope.id
        
        response = client.get(f"/api/reports/{report_id}/preview-sql", params={"cycle_code": test_cycle_code})
        assert response.status_code == 200
        
        preview = response.json()
        assert "sql_previews" in preview
        assert "parameters" in preview
        assert "summary" in preview


class TestReportSummary:
    """Test report summary and listing functionality"""

    def test_get_reports_summary(self, client: TestClient, sample_report_deal_scope, sample_report_tranche_scope):
        """Test getting report summaries"""
        response = client.get("/api/reports/summary")
        assert response.status_code == 200
        
        summaries = response.json()
        assert len(summaries) == 2
        
        for summary in summaries:
            assert "id" in summary
            assert "name" in summary
            assert "scope" in summary
            assert "deal_count" in summary
            assert "tranche_count" in summary
            assert "calculation_count" in summary
            assert "total_executions" in summary


class TestAvailableCalculations:
    """Test available calculations for report building"""

    def test_get_available_calculations_deal_scope(self, client: TestClient, sample_user_calculations, 
                                                 sample_system_calculations):
        """Test getting available calculations for DEAL scope"""
        response = client.get("/api/reports/calculations/available/deal")
        assert response.status_code == 200
        
        calculations = response.json()
        assert len(calculations) > 0
        
        # Should include static fields, user calculations, and system calculations
        calc_types = {calc.get("calculation_type") for calc in calculations}
        assert "STATIC_FIELD" in calc_types
        assert "USER_DEFINED" in calc_types
        assert "SYSTEM_SQL" in calc_types
        
        # Check calculation structure
        for calc in calculations:
            assert "id" in calc
            assert "name" in calc
            assert "scope" in calc
            assert calc["scope"] == "DEAL"
            assert "category" in calc

    def test_get_available_calculations_tranche_scope(self, client: TestClient, sample_user_calculations):
        """Test getting available calculations for TRANCHE scope"""
        response = client.get("/api/reports/calculations/available/tranche")
        assert response.status_code == 200
        
        calculations = response.json()
        assert len(calculations) > 0
        
        # All calculations should be TRANCHE compatible
        for calc in calculations:
            assert calc["scope"] == "TRANCHE"

    def test_get_available_calculations_invalid_scope(self, client: TestClient):
        """Test getting available calculations with invalid scope"""
        response = client.get("/api/reports/calculations/available/invalid")
        assert response.status_code == 400


class TestDataEndpoints:
    """Test data endpoints for report building"""

    def test_get_available_deals(self, client: TestClient, sample_deals):
        """Test getting available deals"""
        response = client.get("/api/reports/data/deals")
        assert response.status_code == 200
        
        deals = response.json()
        assert len(deals) == 3
        
        for deal in deals:
            assert "dl_nbr" in deal
            assert "issr_cde" in deal
            assert "cdi_file_nme" in deal

    def test_get_available_deals_filtered_by_issuer(self, client: TestClient, sample_deals):
        """Test getting deals filtered by issuer code"""
        response = client.get("/api/reports/data/deals", params={"issuer_code": "FHLMC"})
        assert response.status_code == 200
        
        deals = response.json()
        assert len(deals) == 1
        assert deals[0]["issr_cde"] == "FHLMC"

    def test_get_available_tranches(self, client: TestClient, api_headers, sample_tranches):
        """Test getting available tranches for deals"""
        request_data = {
            "dl_nbrs": [1001, 1002],
            "cycle_code": 202404
        }
        
        response = client.post("/api/reports/data/tranches", json=request_data, headers=api_headers)
        assert response.status_code == 200
        
        tranches_by_deal = response.json()
        assert "1001" in tranches_by_deal
        assert "1002" in tranches_by_deal
        
        # Each deal should have tranches
        for deal_id, tranches in tranches_by_deal.items():
            assert len(tranches) > 0
            for tranche in tranches:
                assert "tr_id" in tranche
                assert "dl_nbr" in tranche

    def test_get_available_cycles(self, client: TestClient, sample_tranche_balances):
        """Test getting available cycle codes"""
        response = client.get("/api/reports/data/cycles")
        assert response.status_code == 200
        
        cycles = response.json()
        assert len(cycles) > 0
        
        for cycle in cycles:
            assert "label" in cycle
            assert "value" in cycle

    def test_get_issuer_codes(self, client: TestClient, sample_deals):
        """Test getting available issuer codes"""
        response = client.get("/api/reports/data/issuer-codes")
        assert response.status_code == 200
        
        issuer_codes = response.json()
        assert len(issuer_codes) == 3
        assert "FHLMC" in issuer_codes
        assert "GNMA" in issuer_codes
        assert "PRIVATE" in issuer_codes


class TestColumnPreferences:
    """Test column preferences functionality"""

    def test_report_with_column_preferences(self, client: TestClient, sample_report_deal_scope):
        """Test that reports maintain column preferences"""
        report_id = sample_report_deal_scope.id
        
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 200
        
        report = response.json()
        assert report["column_preferences"] is not None
        assert "columns" in report["column_preferences"]
        
        columns = report["column_preferences"]["columns"]
        assert len(columns) == 3
        
        # Check column preference structure
        for col in columns:
            assert "column_id" in col
            assert "display_name" in col
            assert "is_visible" in col
            assert "display_order" in col
            assert "format_type" in col

    def test_update_column_preferences(self, client: TestClient, api_headers, sample_report_deal_scope):
        """Test updating column preferences"""
        report_id = sample_report_deal_scope.id
        
        update_data = {
            "column_preferences": {
                "columns": [
                    {
                        "column_id": "static_deal.dl_nbr",
                        "display_name": "Deal ID",
                        "is_visible": True,
                        "display_order": 0,
                        "format_type": "number"
                    },
                    {
                        "column_id": "user.tr_end_bal_amt",
                        "display_name": "Balance Total",
                        "is_visible": False,  # Hidden column
                        "display_order": 1,
                        "format_type": "currency"
                    }
                ]
            }
        }
        
        response = client.patch(f"/api/reports/{report_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        
        updated_report = response.json()
        columns = updated_report["column_preferences"]["columns"]
        assert len(columns) == 2
        assert columns[0]["display_name"] == "Deal ID"
        assert not columns[1]["is_visible"]  # Hidden column