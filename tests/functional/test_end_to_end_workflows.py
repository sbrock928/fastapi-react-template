"""
End-to-end functional tests for report creation, execution, and management workflows.
Tests complete user scenarios from report building to execution.
"""

import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient


class TestReportBuildingWorkflow:
    """Test complete report building workflows"""

    def test_create_deal_report_workflow(self, client: TestClient, api_headers, sample_deals, 
                                       sample_user_calculations, sample_system_calculations,
                                       sample_tranche_balances, test_cycle_code):
        """Test complete workflow: create deal report -> run -> verify results"""
        
        # Step 1: Get available calculations for DEAL scope
        response = client.get("/api/reports/calculations/available/deal")
        assert response.status_code == 200
        available_calcs = response.json()
        
        # Should have static, user, and system calculations
        calc_types = {calc["calculation_type"] for calc in available_calcs}
        assert "STATIC_FIELD" in calc_types
        assert "USER_DEFINED" in calc_types
        assert "SYSTEM_SQL" in calc_types
        
        # Step 2: Get available deals
        response = client.get("/api/reports/data/deals")
        assert response.status_code == 200
        deals = response.json()
        assert len(deals) >= 2
        
        # Step 3: Create report with mixed calculation types
        report_data = {
            "name": "End-to-End Deal Report",
            "description": "Complete workflow test report",
            "scope": "DEAL",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [
                {"dl_nbr": 1001, "selected_tranches": []},
                {"dl_nbr": 1002, "selected_tranches": []}
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
                },
                {
                    "calculation_id": f"system.{sample_system_calculations[0].result_column_name}",
                    "calculation_type": "system",
                    "display_order": 2,
                    "display_name": "Issuer Type"
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
        }
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200
        created_report = response.json()
        report_id = created_report["id"]
        
        # Step 4: Get report structure for preview
        response = client.get(f"/api/reports/{report_id}/structure")
        assert response.status_code == 200
        structure = response.json()
        assert len(structure["columns"]) == 3
        assert structure["deal_count"] == 2
        
        # Step 5: Preview SQL
        response = client.get(f"/api/reports/{report_id}/preview-sql", params={"cycle_code": test_cycle_code})
        assert response.status_code == 200
        preview = response.json()
        assert "sql_previews" in preview
        # System includes default columns (deal_number, tranche_id, cycle_code) plus user selections
        assert len(preview["sql_previews"]) >= 3  # At least the 3 selected calculations
        
        # Step 6: Run the report
        run_request = {"cycle_code": test_cycle_code}
        response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        assert "data" in result
        assert "columns" in result
        assert len(result["data"]) == 2  # Two deals
        assert len(result["columns"]) == 3  # Three calculations
        
        # Step 7: Verify data integrity
        data = result["data"]
        for row in data:
            # Should have all calculation results
            assert any("deal" in k.lower() for k in row.keys())  # Deal number
            assert any("balance" in k.lower() for k in row.keys())  # Total balance
            assert any("issuer" in k.lower() or "type" in k.lower() for k in row.keys())  # Issuer type
            
            # Values should be reasonable - handle both raw and formatted values
            deal_num_keys = [k for k in row.keys() if "deal" in k.lower()]
            if deal_num_keys:
                deal_num = row[deal_num_keys[0]]
                # Deal number should be formatted as string with commas due to "number" format
                if isinstance(deal_num, str):
                    # Remove commas to get the raw number for comparison
                    raw_deal_num = int(deal_num.replace(',', ''))
                    assert raw_deal_num in [1001, 1002]
                    # Verify the formatting is applied correctly
                    assert deal_num in ['1,001', '1,002']
                else:
                    # Fallback for raw numbers (if formatting isn't applied)
                    assert deal_num in [1001, 1002]
            
            # Balance should be formatted as currency
            balance_keys = [k for k in row.keys() if "balance" in k.lower()]
            if balance_keys:
                balance = row[balance_keys[0]]
                # Should be formatted as currency string (starts with $ and has commas)
                if isinstance(balance, str):
                    assert balance.startswith('$')
                    assert ',' in balance  # Should have comma separators
                else:
                    # Fallback: should be a reasonable balance amount
                    assert isinstance(balance, (int, float))
                    assert balance > 0

    def test_create_tranche_report_workflow(self, client: TestClient, api_headers, sample_deals,
                                          sample_tranches, sample_user_calculations,
                                          sample_tranche_balances, test_cycle_code):
        """Test complete workflow for tranche-scoped report"""
        
        # Step 1: Get available calculations for TRANCHE scope
        response = client.get("/api/reports/calculations/available/tranche")
        assert response.status_code == 200
        available_calcs = response.json()
        assert len(available_calcs) > 0
        
        # Step 2: Get tranches for specific deal
        tranche_request = {"dl_nbrs": [1001], "cycle_code": test_cycle_code}
        response = client.post("/api/reports/data/tranches", json=tranche_request, headers=api_headers)
        assert response.status_code == 200
        tranches_data = response.json()
        assert "1001" in tranches_data
        deal_tranches = tranches_data["1001"]
        assert len(deal_tranches) >= 2
        
        # Step 3: Create tranche report
        report_data = {
            "name": "End-to-End Tranche Report",
            "description": "Tranche workflow test",
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
        report_id = created_report["id"]
        
        # Step 4: Run tranche report
        run_request = {"cycle_code": test_cycle_code}
        response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        data = result["data"]
        assert len(data) == 2  # Two tranches (A and B)
        
        # Verify tranche-specific data
        for row in data:
            assert any("deal" in k.lower() for k in row.keys())
            assert any("tranche" in k.lower() for k in row.keys())
            
            # Should have specific tranche IDs
            tranche_keys = [k for k in row.keys() if "tranche" in k.lower()]
            if tranche_keys:
                tranche_id = row[tranche_keys[0]]
                assert tranche_id in ["A", "B"]

    def test_report_update_workflow(self, client: TestClient, api_headers, sample_report_deal_scope,
                                  sample_user_calculations, test_cycle_code):
        """Test updating an existing report and re-running"""
        
        report_id = sample_report_deal_scope.id
        
        # Step 1: Get original report
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 200
        original_report = response.json()
        original_calc_count = len(original_report["selected_calculations"])
        
        # Step 2: Update report with additional calculation
        update_data = {
            "name": "Updated Deal Report",
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0,
                    "display_name": "Deal Number"
                },
                {
                    "calculation_id": f"user.{sample_user_calculations[1].source_field}",  # Different user calc
                    "calculation_type": "user",
                    "display_order": 1,
                    "display_name": "Average Rate"
                }
            ]
        }
        
        response = client.patch(f"/api/reports/{report_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        updated_report = response.json()
        assert updated_report["name"] == "Updated Deal Report"
        assert len(updated_report["selected_calculations"]) == 2
        
        # Step 3: Run updated report
        run_request = {"cycle_code": test_cycle_code}
        response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["columns"]) == 2  # Two calculations now


class TestReportManagementWorkflows:
    """Test report management scenarios"""

    def test_report_lifecycle_management(self, client: TestClient, api_headers, sample_deals,
                                       sample_user_calculations, test_cycle_code):
        """Test complete lifecycle: create -> run -> update -> run -> delete"""
        
        # Create report
        report_data = {
            "name": "Lifecycle Test Report",
            "description": "Testing full lifecycle",
            "scope": "DEAL",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [{"dl_nbr": 1001, "selected_tranches": []}],
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0,
                    "display_name": "Deal Number"
                }
            ]
        }
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200
        report = response.json()
        report_id = report["id"]
        
        # Run report
        run_request = {"cycle_code": test_cycle_code}
        response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
        assert response.status_code == 200
        
        # Update report
        update_data = {"description": "Updated lifecycle description"}
        response = client.patch(f"/api/reports/{report_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        
        # Run again
        response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
        assert response.status_code == 200
        
        # Delete report
        response = client.delete(f"/api/reports/{report_id}")
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 404

    def test_multiple_reports_management(self, client: TestClient, api_headers, sample_deals,
                                       sample_user_calculations, test_cycle_code):
        """Test managing multiple reports"""
        
        # Create multiple reports
        report_ids = []
        for i in range(3):
            report_data = {
                "name": f"Multi Report {i+1}",
                "description": f"Report number {i+1}",
                "scope": "DEAL",
                "created_by": "test_user",
                "is_active": True,
                "selected_deals": [{"dl_nbr": 1001, "selected_tranches": []}],
                "selected_calculations": [
                    {
                        "calculation_id": "static_deal.dl_nbr",
                        "calculation_type": "static",
                        "display_order": 0,
                        "display_name": "Deal Number"
                    }
                ]
            }
            
            response = client.post("/api/reports/", json=report_data, headers=api_headers)
            assert response.status_code == 200
            report_ids.append(response.json()["id"])
        
        # Get all reports
        response = client.get("/api/reports/")
        assert response.status_code == 200
        all_reports = response.json()
        created_report_names = {r["name"] for r in all_reports if r["id"] in report_ids}
        assert "Multi Report 1" in created_report_names
        assert "Multi Report 2" in created_report_names
        assert "Multi Report 3" in created_report_names
        
        # Get summary
        response = client.get("/api/reports/summary")
        assert response.status_code == 200
        summaries = response.json()
        assert len([s for s in summaries if s["id"] in report_ids]) == 3
        
        # Run each report
        for report_id in report_ids:
            run_request = {"cycle_code": test_cycle_code}
            response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
            assert response.status_code == 200


class TestCalculationCompatibilityWorkflows:
    """Test calculation compatibility and scope handling"""

    def test_deal_scope_calculation_compatibility(self, client: TestClient, api_headers, sample_deals,
                                                 sample_user_calculations, sample_system_calculations):
        """Test that only compatible calculations work with DEAL scope"""
        
        # Get deal-level calculations
        response = client.get("/api/reports/calculations/available/deal")
        assert response.status_code == 200
        deal_calcs = response.json()
        
        # Filter to only deal-level user and system calculations
        deal_user_calcs = [c for c in deal_calcs if c.get("calculation_type") == "USER_DEFINED"]
        deal_system_calcs = [c for c in deal_calcs if c.get("calculation_type") == "SYSTEM_SQL"]
        
        # All should be compatible with DEAL scope
        for calc in deal_user_calcs + deal_system_calcs:
            assert calc["scope"] == "DEAL"
        
        # Create report with deal-level calculations
        report_data = {
            "name": "Deal Compatibility Test",
            "scope": "DEAL",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [{"dl_nbr": 1001, "selected_tranches": []}],
            "selected_calculations": [
                {
                    "calculation_id": "static_deal.dl_nbr",
                    "calculation_type": "static",
                    "display_order": 0,
                    "display_name": "Deal Number"
                }
            ]
        }
        
        # Add available deal-level calculations
        if deal_user_calcs:
            calc = deal_user_calcs[0]
            report_data["selected_calculations"].append({
                "calculation_id": calc["id"],
                "calculation_type": "user",
                "display_order": 1,
                "display_name": calc["name"]
            })
        
        if deal_system_calcs:
            calc = deal_system_calcs[0]
            report_data["selected_calculations"].append({
                "calculation_id": calc["id"],
                "calculation_type": "system",
                "display_order": 2,
                "display_name": calc["name"]
            })
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200

    def test_tranche_scope_calculation_compatibility(self, client: TestClient, api_headers, sample_deals,
                                                   sample_user_calculations):
        """Test that tranche-compatible calculations work with TRANCHE scope"""
        
        # Get tranche-level calculations
        response = client.get("/api/reports/calculations/available/tranche")
        assert response.status_code == 200
        tranche_calcs = response.json()
        
        # Should include both deal and tranche level calculations
        tranche_user_calcs = [c for c in tranche_calcs if c.get("calculation_type") == "USER_DEFINED"]
        
        # Create report with tranche calculations
        report_data = {
            "name": "Tranche Compatibility Test",
            "scope": "TRANCHE",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [
                {
                    "dl_nbr": 1001,
                    "selected_tranches": [{"tr_id": "A", "dl_nbr": 1001}]
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
                }
            ]
        }
        
        # Add tranche-compatible user calculations
        if tranche_user_calcs:
            calc = tranche_user_calcs[0]
            report_data["selected_calculations"].append({
                "calculation_id": calc["id"],
                "calculation_type": "user",
                "display_order": 2,
                "display_name": calc["name"]
            })
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200


class TestColumnPreferencesWorkflows:
    """Test column preferences and formatting workflows"""

    def test_column_preferences_management_workflow(self, client: TestClient, api_headers, sample_deals,
                                                  sample_user_calculations, test_cycle_code):
        """Test complete column preferences workflow"""
        
        # Step 1: Create report with column preferences
        report_data = {
            "name": "Column Preferences Test",
            "scope": "DEAL",
            "created_by": "test_user",
            "is_active": True,
            "selected_deals": [{"dl_nbr": 1001, "selected_tranches": []}],
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
                        "display_name": "Deal ID",
                        "is_visible": True,
                        "display_order": 0,
                        "format_type": "number"
                    },
                    {
                        "column_id": f"user.{sample_user_calculations[0].source_field}",
                        "display_name": "Balance ($)",
                        "is_visible": True,
                        "display_order": 1,
                        "format_type": "currency"
                    }
                ]
            }
        }
        
        response = client.post("/api/reports/", json=report_data, headers=api_headers)
        assert response.status_code == 200
        report = response.json()
        report_id = report["id"]
        
        # Step 2: Verify column preferences are saved
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 200
        saved_report = response.json()
        
        column_prefs = saved_report["column_preferences"]
        assert column_prefs is not None
        assert len(column_prefs["columns"]) == 2
        assert column_prefs["columns"][0]["display_name"] == "Deal ID"
        assert column_prefs["columns"][1]["display_name"] == "Balance ($)"
        assert column_prefs["columns"][1]["format_type"] == "currency"
        
        # Step 3: Run report and verify column metadata
        run_request = {"cycle_code": test_cycle_code}
        response = client.post(f"/api/reports/run/{report_id}", json=run_request, headers=api_headers)
        assert response.status_code == 200
        
        result = response.json()
        columns = result["columns"]
        assert len(columns) == 2
        
        # Column metadata should reflect preferences
        deal_col = next(c for c in columns if "deal" in c["field"].lower())
        balance_col = next(c for c in columns if "balance" in c["header"].lower())
        
        assert deal_col["format_type"] == "number"
        assert balance_col["format_type"] == "currency"
        
        # Step 4: Update column preferences
        update_data = {
            "column_preferences": {
                "columns": [
                    {
                        "column_id": "static_deal.dl_nbr",
                        "display_name": "Deal Number",  # Changed
                        "is_visible": True,
                        "display_order": 1,  # Reordered
                        "format_type": "number"
                    },
                    {
                        "column_id": f"user.{sample_user_calculations[0].source_field}",
                        "display_name": "Total Amount",  # Changed
                        "is_visible": False,  # Hidden
                        "display_order": 0,  # Reordered
                        "format_type": "currency"
                    }
                ]
            }
        }
        
        response = client.patch(f"/api/reports/{report_id}", json=update_data, headers=api_headers)
        assert response.status_code == 200
        
        # Step 5: Verify updated preferences
        response = client.get(f"/api/reports/{report_id}")
        assert response.status_code == 200
        updated_report = response.json()
        
        updated_prefs = updated_report["column_preferences"]["columns"]
        assert updated_prefs[0]["display_name"] == "Deal Number"
        assert not updated_prefs[1]["is_visible"]  # Hidden column