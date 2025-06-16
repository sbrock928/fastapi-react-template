# scripts/create_cdi_calculations.py
"""
Migration script to create CDI Variable calculations based on existing requirements.
Run this after implementing the CDI Variable system.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, get_dw_db
from app.calculations.service import SystemCalculationService
from app.calculations.dao import SystemCalculationDAO
from app.calculations.cdi_service import CDIVariableCalculationService
from app.calculations.cdi_schemas import CDIVariableCreate


def create_cdi_variable_calculations():
    """Create the CDI variable calculations based on the original query requirements"""
    
    # Create database sessions
    config_db = SessionLocal()
    dw_db = next(get_dw_db())
    
    try:
        # Initialize services
        system_calc_dao = SystemCalculationDAO(config_db)
        system_calc_service = SystemCalculationService(system_calc_dao)
        cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
        
        # Define the default tranche mappings based on your original query
        default_tranche_mappings = {
            "M1": ["1M1", "2M1", "M1"],
            "M2": ["1M2", "2M2", "M2"],
            "B1": ["1B1", "2B1", "B1"],
            "B2": ["B2", "1B2", "2B2"],
            "B1_INV": ["1B1_INV", "2B1_INV"],
            "M1_INV": ["1M1_INV"],
            "M2_INV": ["1M2_INV"],
            "A1_INV": ["1A1_INV"],
            "1M2": ["1M2"],
            "2M2": ["2M2"],
            "1B1": ["1B1"],
            "2B1": ["2B1"]
        }
        
        # Define CDI variable calculations to create
        cdi_calculations = [
            {
                "name": "Investment Income",
                "description": "Investment income calculation from CDI variables (#RPT_RRI_*)",
                "variable_pattern": "#RPT_RRI_{tranche_suffix}",
                "variable_type": "investment_income",
                "result_column_name": "investment_income",
                "tranche_mappings": default_tranche_mappings
            },
            {
                "name": "Excess Interest",
                "description": "Excess interest calculation from CDI variables (#RPT_EXC_*)",
                "variable_pattern": "#RPT_EXC_{tranche_suffix}",
                "variable_type": "excess_interest", 
                "result_column_name": "excess_interest",
                "tranche_mappings": default_tranche_mappings
            },
            {
                "name": "Principal Payments",
                "description": "Principal payment calculation from CDI variables (#RPT_PRINC_*)",
                "variable_pattern": "#RPT_PRINC_{tranche_suffix}",
                "variable_type": "principal",
                "result_column_name": "principal_payments",
                "tranche_mappings": default_tranche_mappings
            },
            {
                "name": "Interest Payments", 
                "description": "Interest payment calculation from CDI variables (#RPT_INT_*)",
                "variable_pattern": "#RPT_INT_{tranche_suffix}",
                "variable_type": "interest",
                "result_column_name": "interest_payments",
                "tranche_mappings": default_tranche_mappings
            },
            {
                "name": "Servicing Fees",
                "description": "Servicing fees calculation from CDI variables (#RPT_FEES_*)",
                "variable_pattern": "#RPT_FEES_{tranche_suffix}",
                "variable_type": "fees",
                "result_column_name": "servicing_fees",
                "tranche_mappings": default_tranche_mappings
            }
        ]
        
        created_count = 0
        failed_count = 0
        
        print("Creating CDI Variable calculations...")
        print("=" * 50)
        
        for calc_config in cdi_calculations:
            try:
                # Check if calculation already exists
                existing_calcs = cdi_service.get_all_cdi_variable_calculations()
                if any(calc.name == calc_config["name"] for calc in existing_calcs):
                    print(f"⚠️  '{calc_config['name']}' already exists, skipping...")
                    continue
                
                # Create the CDI variable calculation
                request = CDIVariableCreate(**calc_config)
                created_calc = cdi_service.create_cdi_variable_calculation(request, "system_migration")
                
                print(f"✅ Created '{created_calc.name}' (ID: {created_calc.id})")
                created_count += 1
                
            except Exception as e:
                print(f"❌ Failed to create '{calc_config['name']}': {str(e)}")
                failed_count += 1
        
        print("=" * 50)
        print(f"Migration completed:")
        print(f"  ✅ Created: {created_count}")
        print(f"  ❌ Failed: {failed_count}")
        
        if created_count > 0:
            print("\n📋 Next steps:")
            print("1. Test the calculations using the /cdi-variables/{id}/execute endpoint")
            print("2. Add these calculations to your report templates")
            print("3. Configure any additional tranche mappings as needed")
            
            print("\n🔧 Example API call to test Investment Income calculation:")
            print("POST /api/calculations/cdi-variables/execute")
            print("""{
    "calculation_id": 1,
    "cycle_code": 12503,
    "deal_numbers": [12345, 12346]
}""")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    
    finally:
        config_db.close()
        if hasattr(dw_db, 'close'):
            dw_db.close()


def create_sample_tranche_specific_calculations():
    """Create additional calculations for specific tranche types that appear in your original query"""
    
    config_db = SessionLocal()
    dw_db = next(get_dw_db())
    
    try:
        system_calc_dao = SystemCalculationDAO(config_db)
        system_calc_service = SystemCalculationService(system_calc_dao)
        cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
        
        # Specific calculations based on your original query patterns
        specific_calculations = [
            {
                "name": "Investment Income - 1M2 Specific",
                "description": "Investment income for 1M2 tranche specifically",
                "variable_pattern": "#RPT_RRI_{tranche_suffix}",  # FIXED: Added placeholder
                "variable_type": "investment_income_specific",
                "result_column_name": "investment_income_1m2",
                "tranche_mappings": {"1M2": ["1M2"]}
            },
            {
                "name": "Investment Income - 2M2 Specific", 
                "description": "Investment income for 2M2 tranche specifically",
                "variable_pattern": "#RPT_RRI_{tranche_suffix}",  # FIXED: Added placeholder
                "variable_type": "investment_income_specific",
                "result_column_name": "investment_income_2m2",
                "tranche_mappings": {"2M2": ["2M2"]}
            },
            {
                "name": "Investment Income - 1B1 Specific",
                "description": "Investment income for 1B1 tranche specifically", 
                "variable_pattern": "#RPT_RRI_{tranche_suffix}",  # FIXED: Added placeholder
                "variable_type": "investment_income_specific",
                "result_column_name": "investment_income_1b1",
                "tranche_mappings": {"1B1": ["1B1"]}
            },
            {
                "name": "Investment Income - 2B1 Specific",
                "description": "Investment income for 2B1 tranche specifically",
                "variable_pattern": "#RPT_RRI_{tranche_suffix}",  # FIXED: Added placeholder
                "variable_type": "investment_income_specific",
                "result_column_name": "investment_income_2b1",
                "tranche_mappings": {"2B1": ["2B1"]}
            }
        ]
        
        print("\nCreating tranche-specific CDI calculations...")
        print("=" * 50)
        
        for calc_config in specific_calculations:
            try:
                request = CDIVariableCreate(**calc_config)
                created_calc = cdi_service.create_cdi_variable_calculation(request, "system_migration")
                print(f"✅ Created '{created_calc.name}' (ID: {created_calc.id})")
                
            except Exception as e:
                print(f"❌ Failed to create '{calc_config['name']}': {str(e)}")
        
    finally:
        config_db.close()
        if hasattr(dw_db, 'close'):
            dw_db.close()


def validate_cdi_calculations():
    """Validate that the created CDI calculations work properly"""
    
    config_db = SessionLocal()
    dw_db = next(get_dw_db())
    
    try:
        system_calc_dao = SystemCalculationDAO(config_db)
        system_calc_service = SystemCalculationService(system_calc_dao)
        cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
        
        print("\n🔍 Validating CDI calculations...")
        print("=" * 50)
        
        cdi_calcs = cdi_service.get_all_cdi_variable_calculations()
        
        for calc in cdi_calcs:
            try:
                # Test the SQL generation
                test_sql = cdi_service._generate_dynamic_sql(
                    calc.variable_pattern,
                    calc.tranche_mappings,
                    12503,  # Sample cycle code
                    [12345]  # Sample deal number
                )
                
                print(f"✅ '{calc.name}': SQL generation successful")
                
                # Optionally test execution (commented out to avoid errors if no data)
                # result = cdi_service.execute_cdi_variable_calculation(calc.id, 12503, [12345])
                # print(f"   Execution test: {len(result)} rows returned")
                
            except Exception as e:
                print(f"❌ '{calc.name}': Validation failed - {str(e)}")
        
    finally:
        config_db.close()
        if hasattr(dw_db, 'close'):
            dw_db.close()


if __name__ == "__main__":
    print("🚀 Starting CDI Variable Calculation Migration")
    print("=" * 60)
    
    # Run the main migration
    create_cdi_variable_calculations()
    
    # Ask user if they want to create specific calculations
    response = input("\n❓ Create tranche-specific calculations? (y/N): ")
    if response.lower() in ['y', 'yes']:
        create_sample_tranche_specific_calculations()
    
    # Validate the calculations
    response = input("\n❓ Run validation tests? (y/N): ")
    if response.lower() in ['y', 'yes']:
        validate_cdi_calculations()
    
    print("\n🎉 Migration completed!")
    print("\n📚 Documentation:")
    print("- API endpoints available at /api/calculations/cdi-variables/")
    print("- Configuration endpoint: GET /api/calculations/cdi-variables/config")
    print("- Execute calculation: POST /api/calculations/cdi-variables/{id}/execute")