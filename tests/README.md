# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the FastAPI React Template's reporting and calculations features. It's designed to ensure that all functionality works correctly before and after refactoring, with a focus on API endpoints and functional workflows.

## Test Structure

```
tests/
├── __init__.py                              # Test package initialization
├── conftest.py                              # Shared fixtures and configuration
├── run_tests.py                             # Test runner script
├── unit/                                    # Unit tests
│   └── test_reporting_service.py            # Service logic tests
├── functional/                              # Functional/integration tests
│   ├── test_reporting_api.py                # Reporting API tests
│   ├── test_calculations_api.py             # Calculations API tests
│   └── test_end_to_end_workflows.py         # Complete user workflows
└── fixtures/                                # Test data fixtures (empty for now)
```

## Test Categories

### 🔧 Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual service methods and business logic
- **Coverage**: Service layer validation, calculation resolution, column preferences

### 🌐 Functional Tests  
- **Location**: `tests/functional/`
- **Purpose**: Test complete API endpoints and user workflows
- **Coverage**: CRUD operations, report execution, mixed calculation types

### 📊 End-to-End Tests
- **Location**: `tests/functional/test_end_to_end_workflows.py`
- **Purpose**: Test complete user scenarios from start to finish
- **Coverage**: Report building, execution, management lifecycles

## Key Test Features

### 🎯 **Mixed Calculation Types Testing**
Tests the core functionality you're most concerned about:
- **User calculations** (`user.{source_field}` format)
- **System calculations** (`system.{result_column}` format)  
- **Static fields** (`static_{table}.{field}` format)
- **Mixed reports** with all three types together

### 🏗️ **Deal vs Tranche Scope Compatibility**
Ensures calculations work correctly at both scopes:
- Deal-level aggregations and compatibility
- Tranche-level calculations and data integrity
- Scope validation and error handling

### 🎨 **Column Preferences Management**
Tests the column management system:
- Creation and update of column preferences
- Display order and formatting
- Visibility controls and metadata

### 🔄 **Report CRUD Operations**
Comprehensive testing of report lifecycle:
- Create reports with validation
- Update reports and re-run
- Delete reports (soft delete)
- List and summary operations

## Quick Start

### 1. Install Dependencies
```bash
python tests/run_tests.py install
```

### 2. Run All Tests
```bash
python tests/run_tests.py all
```

### 3. Run Specific Test Categories
```bash
# Run only API tests
python tests/run_tests.py api

# Run only reporting tests
python tests/run_tests.py reporting

# Run only calculations tests  
python tests/run_tests.py calculations

# Run with coverage report
python tests/run_tests.py coverage
```

## Test Database Setup

The test suite uses **in-memory SQLite databases** for both:
- **Config database**: Reports, calculations, preferences
- **Data warehouse**: Deals, tranches, balance data

### Sample Data
Each test gets fresh sample data including:
- **3 deals** (FHLMC, GNMA, Private issuer types)
- **9 tranches** (A, B, C for each deal)
- **36 tranche balances** (4 cycles × 9 tranches)
- **3 user calculations** (deal-level, tranche-level, weighted average)
- **2 system calculations** (issuer type, deal status)

## Test Fixtures

### Core Fixtures
- `client`: FastAPI test client with database overrides
- `sample_deals`: Test deal data
- `sample_tranches`: Test tranche data  
- `sample_tranche_balances`: Test balance data
- `sample_user_calculations`: Test user calculations
- `sample_system_calculations`: Test system calculations
- `sample_report_deal_scope`: Complete deal-scoped report
- `sample_report_tranche_scope`: Complete tranche-scoped report

### Utility Fixtures
- `api_headers`: Standard HTTP headers
- `test_cycle_code`: Standard cycle for testing (202404)

## Critical Test Scenarios

### ✅ **Mixed Calculation Report Creation & Execution**
Tests creating and running reports with:
- Static fields (deal.dl_nbr, tranche.tr_id)
- User calculations (balance aggregations, rates)
- System calculations (issuer categorization)

### ✅ **Scope Compatibility Validation**
Ensures:
- Deal-scope reports only get compatible calculations
- Tranche-scope reports get both deal and tranche calculations
- Proper error handling for invalid combinations

### ✅ **Column Preferences Workflow**
Tests:
- Creating reports with custom column preferences
- Updating preferences and re-running reports
- Format types (currency, number, text, date)
- Display order and visibility controls

### ✅ **Report Lifecycle Management**
Covers:
- Create → Run → Update → Run → Delete workflows
- Multiple reports management
- Report summaries and metadata

## Running Tests During Development

### Before Making Changes
```bash
# Establish baseline - all tests should pass
python tests/run_tests.py all
```

### During Refactoring
```bash
# Run frequently to catch regressions
python tests/run_tests.py reporting
python tests/run_tests.py calculations
```

### After Changes
```bash
# Full test suite with coverage
python tests/run_tests.py coverage
```

## Test Data Validation

The tests verify that your core functionality works correctly:

1. **Report Creation**: Can create reports with mixed calculation types
2. **Report Execution**: Reports generate correct data for selected deals/tranches
3. **Calculation Resolution**: New ID format (`user.field`, `system.column`, `static_table.field`) resolves properly
4. **Column Management**: Preferences are saved and applied correctly
5. **Scope Handling**: Deal vs tranche scopes work as expected

## Expected Test Results

When all tests pass, you can be confident that:
- ✅ Report create/update/delete functionality works correctly
- ✅ Mixed calculation types (system, user, static) execute properly
- ✅ Deal and tranche scope compatibility is maintained
- ✅ Column preferences are handled correctly
- ✅ The API endpoints return proper data structures
- ✅ End-to-end workflows complete successfully

This test suite is designed to give you confidence during your dynamic refactor by ensuring all the core reporting and calculations functionality continues to work as expected.