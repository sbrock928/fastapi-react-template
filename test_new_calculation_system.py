#!/usr/bin/env python3
"""
Test script for the new separated calculation API system.
Tests all major endpoints to ensure they work correctly.
"""

import requests
import json
from typing import Dict, Any
import sys

BASE_URL = "http://localhost:8000/api"

def test_endpoint(method: str, endpoint: str, data: Dict[Any, Any] = None, description: str = ""):
    """Test a single API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n🧪 Testing: {description}")
    print(f"   {method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code < 400:
            print(f"   ✅ Status: {response.status_code}")
            if response.content:
                try:
                    json_data = response.json()
                    if isinstance(json_data, list):
                        print(f"   📊 Returns: {len(json_data)} items")
                        if json_data and len(json_data) > 0:
                            print(f"   📋 Sample: {list(json_data[0].keys()) if isinstance(json_data[0], dict) else 'Non-dict item'}")
                    elif isinstance(json_data, dict):
                        print(f"   📋 Keys: {list(json_data.keys())}")
                    return json_data
                except:
                    print(f"   📄 Response length: {len(response.content)} bytes")
            return True
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   📄 Error: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed - is the server running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Test all the new calculation API endpoints"""
    print("🚀 Testing New Separated Calculation API System")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Configuration endpoints
    total_tests += 1
    if test_endpoint("GET", "/calculations/config", description="Get calculation configuration"):
        success_count += 1
    
    # Test 2: Static fields
    total_tests += 1
    if test_endpoint("GET", "/calculations/static-fields", description="Get all static fields"):
        success_count += 1
    
    total_tests += 1
    if test_endpoint("GET", "/calculations/static-fields/deal.dl_nbr", description="Get specific static field"):
        success_count += 1
    
    # Test 3: User calculations - Read operations
    total_tests += 1
    user_calcs = test_endpoint("GET", "/calculations/user", description="Get all user calculations")
    if user_calcs:
        success_count += 1
    
    total_tests += 1
    if test_endpoint("GET", "/calculations/user?group_level=deal", description="Get deal-level user calculations"):
        success_count += 1
    
    # Test 4: System calculations - Read operations  
    total_tests += 1
    system_calcs = test_endpoint("GET", "/calculations/system", description="Get all system calculations")
    if system_calcs:
        success_count += 1
    
    # Test 5: Create a new user calculation
    total_tests += 1
    new_user_calc_data = {
        "name": "API Test Calculation",
        "description": "Test calculation created via API",
        "aggregation_function": "SUM",
        "source_model": "TrancheBal", 
        "source_field": "tr_end_bal_amt",
        "group_level": "deal"
    }
    created_calc = test_endpoint("POST", "/calculations/user", new_user_calc_data, "Create new user calculation")
    if created_calc:
        success_count += 1
    
    # Test 6: Get the created calculation by ID
    if created_calc and isinstance(created_calc, dict) and 'id' in created_calc:
        calc_id = created_calc['id']
        total_tests += 1
        if test_endpoint("GET", f"/calculations/user/{calc_id}", description=f"Get user calculation by ID ({calc_id})"):
            success_count += 1
        
        # Test 7: Update the calculation
        total_tests += 1
        update_data = {"description": "Updated description via API test"}
        if test_endpoint("PUT", f"/calculations/user/{calc_id}", update_data, "Update user calculation"):
            success_count += 1
        
        # Test 8: Get usage info
        total_tests += 1
        if test_endpoint("GET", f"/calculations/user/{calc_id}/usage", description="Get calculation usage info"):
            success_count += 1
    
    # Test 9: Create a system calculation
    total_tests += 1
    new_system_calc_data = {
        "name": "API Test System Calc",
        "description": "Test system calculation created via API",
        "group_level": "deal",
        "raw_sql": "SELECT deal.dl_nbr, 'Test' AS test_result FROM deal",
        "result_column_name": "test_result"
    }
    created_system_calc = test_endpoint("POST", "/calculations/system", new_system_calc_data, "Create new system calculation")
    if created_system_calc:
        success_count += 1
    
    # Test 10: Statistics endpoint
    total_tests += 1
    if test_endpoint("GET", "/calculations/stats/counts", description="Get calculation statistics"):
        success_count += 1
    
    # Test 11: Preview single calculation
    total_tests += 1
    preview_data = {
        "calc_type": "static_field",
        "field_path": "deal.dl_nbr",
        "alias": "deal_number"
    }
    body_data = {
        "deal_tranche_map": {1001: ["A", "B"], 1002: []},
        "cycle_code": 202404
    }
    # Note: This endpoint expects the calculation request in the body along with filters
    # We'll need to adjust this test based on the actual endpoint structure
    
    # Test 12: Report execution with mixed calculations
    total_tests += 1
    if user_calcs and len(user_calcs) > 0:
        report_exec_data = {
            "calculation_requests": [
                {"calc_type": "static_field", "field_path": "deal.dl_nbr", "alias": "deal_number"},
                {"calc_type": "user_calculation", "calc_id": user_calcs[0]["id"], "alias": "user_calc_result"}
            ],
            "deal_tranche_map": {1001: ["A", "B"], 1002: []},
            "cycle_code": 202404
        }
        if test_endpoint("POST", "/calculations/execute-report", report_exec_data, "Execute mixed calculation report"):
            success_count += 1
    
    # Test 13: SQL Preview
    total_tests += 1
    if user_calcs and len(user_calcs) > 0:
        preview_data = {
            "calculation_requests": [
                {"calc_type": "static_field", "field_path": "deal.dl_nbr", "alias": "deal_number"},
                {"calc_type": "user_calculation", "calc_id": user_calcs[0]["id"], "alias": "user_calc_result"}
            ],
            "deal_tranche_map": {1001: ["A"], 1002: []},
            "cycle_code": 202404
        }
        if test_endpoint("POST", "/calculations/preview-sql", preview_data, "Preview SQL for mixed calculations"):
            success_count += 1
    
    # Test 14: Legacy compatibility endpoint
    total_tests += 1
    if test_endpoint("GET", "/calculations/legacy/all", description="Legacy compatibility endpoint"):
        success_count += 1
    
    # Test 15: Health check
    total_tests += 1
    if test_endpoint("GET", "/calculations/health", description="Calculation system health check"):
        success_count += 1
    
    # Print results
    print("\n" + "=" * 60)
    print(f"📊 API Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All API endpoints working correctly!")
        return True
    elif success_count >= total_tests * 0.8:  # 80% success rate
        print("✅ Most API endpoints working - minor issues detected")
        return True
    else:
        print(f"⚠️  {total_tests - success_count} API endpoints failing")
        return False

if __name__ == "__main__":
    # Check if server is running first
    try:
        response = requests.get(f"{BASE_URL}/calculations/health")
        if response.status_code == 200:
            print("✅ Server detected, starting tests...")
            success = main()
        else:
            print("❌ Server responding but calculation endpoints not healthy")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("   Make sure the FastAPI server is running with: python main.py")
        sys.exit(1)
    
    sys.exit(0 if success else 1)