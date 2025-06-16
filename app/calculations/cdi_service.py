# app/calculations/cdi_service.py - UPDATED VERSION USING SQLALCHEMY MODELS
"""Service for handling CDI Variable calculations with SQLAlchemy models"""

from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
import pandas as pd
from app.core.exceptions import CalculationNotFoundError, InvalidCalculationError
from .models import SystemCalculation, GroupLevel
from .service import SystemCalculationService
from .cdi_schemas import CDIVariableCreate, CDIVariableResponse, CDIVariableUpdate

# Import the datawarehouse models
from app.datawarehouse.models import DealCdiVarRpt, TrancheBal



class CDIVariableCalculationService:
    """Service for managing CDI Variable calculations using SystemCalculation framework and SQLAlchemy models"""
    
    def __init__(self, dw_db: Session, config_db: Session, system_calc_service: SystemCalculationService):
        self.dw_db = dw_db
        self.config_db = config_db
        self.system_calc_service = system_calc_service
    
    # ===== CDI VARIABLE CRUD OPERATIONS =====
    
    def create_cdi_variable_calculation(self, request: CDIVariableCreate, created_by: str) -> CDIVariableResponse:
        """Create a new CDI variable calculation"""
        
        # Generate the metadata config for CDI variables
        metadata_config = {
            "calculation_type": "cdi_variable",
            "variable_pattern": request.variable_pattern,
            "variable_type": request.variable_type,
            "tranche_mappings": request.tranche_mappings,
            "description": f"CDI Variable calculation for {request.variable_type}",
            "required_models": ["Deal", "TrancheBal", "DealCdiVarRpt"],  # Updated to include CDI model
            "performance_hints": {
                "complexity": "medium",
                "estimated_rows": 1000,
                "uses_orm": True  # Flag that this uses SQLAlchemy models
            }
        }
        
        # Create the SystemCalculation
        from .schemas import SystemCalculationCreate
        system_calc_request = SystemCalculationCreate(
            name=request.name,
            description=request.description,
            raw_sql=self._generate_placeholder_sql(request.variable_pattern),  # Placeholder - real SQL generated at runtime
            result_column_name=request.result_column_name,
            group_level=GroupLevel.TRANCHE,  # CDI variables are always tranche-level
            metadata_config=metadata_config
        )
        
        system_calc = self.system_calc_service.create_system_calculation(system_calc_request, created_by)
        
        return CDIVariableResponse(
            id=system_calc.id,
            name=system_calc.name,
            description=system_calc.description,
            variable_pattern=request.variable_pattern,
            variable_type=request.variable_type,
            result_column_name=system_calc.result_column_name,
            tranche_mappings=request.tranche_mappings,
            created_by=system_calc.created_by,
            created_at=system_calc.created_at,
            is_active=system_calc.is_active
        )
    
    def get_cdi_variable_calculation(self, calc_id: int) -> Optional[CDIVariableResponse]:
        """Get a CDI variable calculation by ID"""
        system_calc = self.system_calc_service.get_system_calculation_by_id(calc_id)
        
        if not system_calc or not self._is_cdi_variable_calculation(system_calc):
            return None
            
        return self._convert_to_cdi_response(system_calc)
    
    def get_all_cdi_variable_calculations(self) -> List[CDIVariableResponse]:
        """Get all CDI variable calculations"""
        all_system_calcs = self.system_calc_service.get_all_system_calculations(group_level="tranche")
        
        cdi_calcs = [
            self._convert_to_cdi_response(calc) 
            for calc in all_system_calcs 
            if self._is_cdi_variable_calculation(calc)
        ]
        
        return cdi_calcs
    
    def update_cdi_variable_calculation(self, calc_id: int, request: CDIVariableUpdate) -> CDIVariableResponse:
        """Update an existing CDI variable calculation"""
        
        # Get the existing calculation
        existing_calc = self.system_calc_service.get_system_calculation_by_id(calc_id)
        if not existing_calc or not self._is_cdi_variable_calculation(existing_calc):
            raise CalculationNotFoundError(f"CDI variable calculation with ID {calc_id} not found")
        
        # Update metadata config
        metadata_config = existing_calc.metadata_config.copy()
        if request.variable_pattern:
            metadata_config["variable_pattern"] = request.variable_pattern
        if request.variable_type:
            metadata_config["variable_type"] = request.variable_type
        if request.tranche_mappings:
            metadata_config["tranche_mappings"] = request.tranche_mappings
        
        # Create system calculation update request
        from .schemas import SystemCalculationUpdate
        system_update = SystemCalculationUpdate(
            name=request.name,
            description=request.description,
            result_column_name=request.result_column_name,
            metadata_config=metadata_config
        )
        
        updated_calc = self.system_calc_service.update_system_calculation(calc_id, system_update)
        return self._convert_to_cdi_response(updated_calc)
    
    # ===== EXECUTION METHODS USING SQLALCHEMY MODELS =====
    
    def execute_cdi_variable_calculation(self, calc_id: int, cycle_code: int, 
                                       deal_numbers: List[int]) -> pd.DataFrame:
        """Execute a CDI variable calculation using SQLAlchemy models"""
        
        system_calc = self.system_calc_service.get_system_calculation_by_id(calc_id)
        if not system_calc or not self._is_cdi_variable_calculation(system_calc):
            raise CalculationNotFoundError(f"CDI variable calculation with ID {calc_id} not found")
        
        metadata = system_calc.metadata_config
        variable_pattern = metadata["variable_pattern"]
        tranche_mappings = metadata["tranche_mappings"]
        
        try:
            # Use SQLAlchemy models instead of raw SQL
            result_data = self._execute_using_models(
                variable_pattern, tranche_mappings, cycle_code, deal_numbers
            )
            
            # Convert to DataFrame
            if result_data:
                result_df = pd.DataFrame(result_data)
                # Ensure consistent column naming
                result_df = result_df.rename(columns={'variable_value': system_calc.result_column_name})
            else:
                # Return empty DataFrame with expected columns
                result_df = pd.DataFrame(columns=['dl_nbr', 'tr_id', 'cycle_cde', system_calc.result_column_name])
            
            return result_df
            
        except Exception as e:
            raise InvalidCalculationError(f"Error executing CDI variable calculation: {str(e)}")
    
    def _execute_using_models(self, variable_pattern: str, tranche_mappings: Dict[str, List[str]], 
                            cycle_code: int, deal_numbers: List[int]) -> List[Dict]:
        """Execute CDI variable calculation using SQLAlchemy models instead of raw SQL"""
        
        all_results = []
        
        # For each tranche suffix, get the corresponding CDI variables
        for tranche_suffix, tr_id_list in tranche_mappings.items():
            # Generate the variable name for this tranche suffix
            variable_name = variable_pattern.replace("{tranche_suffix}", tranche_suffix)
            
            # Query CDI variables using the model
            cdi_vars = (
                self.dw_db.query(DealCdiVarRpt)
                .filter(
                    DealCdiVarRpt.dl_nbr.in_(deal_numbers),
                    DealCdiVarRpt.cycle_cde == cycle_code,
                    DealCdiVarRpt.dl_cdi_var_nme == variable_name.ljust(32)  # Account for CHAR(32) padding
                )
                .all()
            )
            
            # For each CDI variable found, match it with corresponding tranches
            for cdi_var in cdi_vars:
                # Find matching tranches for this deal/cycle with the correct tr_id
                matching_tranches = (
                    self.dw_db.query(TrancheBal)
                    .filter(
                        TrancheBal.dl_nbr == cdi_var.dl_nbr,
                        TrancheBal.cycle_cde == cdi_var.cycle_cde,
                        TrancheBal.tr_id.in_(tr_id_list)
                    )
                    .all()
                )
                
                # Create result records for each matching tranche
                for tranche in matching_tranches:
                    all_results.append({
                        'dl_nbr': cdi_var.dl_nbr,
                        'tr_id': tranche.tr_id,
                        'cycle_cde': cdi_var.cycle_cde,
                        'variable_value': cdi_var.numeric_value,  # Use the model property for numeric conversion
                        'tranche_type': tranche_suffix,
                        'variable_name': cdi_var.variable_name  # Trimmed variable name
                    })
        
        return all_results
    
    # ===== DISCOVERY AND VALIDATION METHODS =====
    
    def discover_available_variables(self, cycle_code: int, deal_numbers: List[int] = None, 
                                   pattern_prefix: str = "#RPT_") -> Dict[str, List[str]]:
        """Discover available CDI variables in the datawarehouse"""
        
        query = self.dw_db.query(DealCdiVarRpt.dl_cdi_var_nme.distinct()).filter(
            DealCdiVarRpt.cycle_cde == cycle_code,
            DealCdiVarRpt.dl_cdi_var_nme.like(f"{pattern_prefix}%")
        )
        
        if deal_numbers:
            query = query.filter(DealCdiVarRpt.dl_nbr.in_(deal_numbers))
        
        variable_names = [name.strip() for name, in query.all()]
        
        # Group by pattern type
        grouped_vars = {}
        for var_name in variable_names:
            # Extract pattern type (e.g., "RRI", "EXC", "PRINC")
            if "_" in var_name:
                parts = var_name.split("_")
                if len(parts) >= 2:
                    pattern_type = parts[1]  # e.g., "RRI" from "#RPT_RRI_M1"
                    if pattern_type not in grouped_vars:
                        grouped_vars[pattern_type] = []
                    grouped_vars[pattern_type].append(var_name)
        
        return grouped_vars
    
    def validate_tranche_mappings(self, tranche_mappings: Dict[str, List[str]], 
                                cycle_code: int, deal_numbers: List[int]) -> Dict[str, Any]:
        """Validate that tranche mappings have corresponding data in the datawarehouse"""
        
        validation_results = {
            "valid_mappings": {},
            "invalid_mappings": {},
            "missing_tranches": [],
            "available_tranches": []
        }
        
        # Get all available tranches for the given deals and cycle
        available_tranches = (
            self.dw_db.query(TrancheBal.tr_id.distinct())
            .filter(
                TrancheBal.dl_nbr.in_(deal_numbers),
                TrancheBal.cycle_cde == cycle_code
            )
            .all()
        )
        
        available_tr_ids = {tr_id for tr_id, in available_tranches}
        validation_results["available_tranches"] = list(available_tr_ids)
        
        # Check each mapping
        for suffix, tr_id_list in tranche_mappings.items():
            valid_tr_ids = [tr_id for tr_id in tr_id_list if tr_id in available_tr_ids]
            invalid_tr_ids = [tr_id for tr_id in tr_id_list if tr_id not in available_tr_ids]
            
            if valid_tr_ids:
                validation_results["valid_mappings"][suffix] = valid_tr_ids
            
            if invalid_tr_ids:
                validation_results["invalid_mappings"][suffix] = invalid_tr_ids
        
        return validation_results
    
    # ===== UTILITY METHODS =====
    
    def _is_cdi_variable_calculation(self, system_calc: SystemCalculation) -> bool:
        """Check if a SystemCalculation is a CDI variable calculation"""
        return (
            system_calc.metadata_config and 
            system_calc.metadata_config.get("calculation_type") == "cdi_variable"
        )
    
    def _convert_to_cdi_response(self, system_calc: SystemCalculation) -> CDIVariableResponse:
        """Convert SystemCalculation to CDIVariableResponse"""
        metadata = system_calc.metadata_config
        
        return CDIVariableResponse(
            id=system_calc.id,
            name=system_calc.name,
            description=system_calc.description,
            variable_pattern=metadata.get("variable_pattern", ""),
            variable_type=metadata.get("variable_type", ""),
            result_column_name=system_calc.result_column_name,
            tranche_mappings=metadata.get("tranche_mappings", {}),
            created_by=system_calc.created_by,
            created_at=system_calc.created_at,
            is_active=system_calc.is_active
        )
    
    def _generate_placeholder_sql(self, variable_pattern: str) -> str:
        """Generate placeholder SQL for SystemCalculation storage"""
        return """SELECT 
    d.dl_nbr,
    t.tr_id, 
    tb.cycle_cde,
    0.0 as calculated_value
FROM deal d
JOIN tranche t ON d.dl_nbr = t.dl_nbr
JOIN tranchebal tb ON t.dl_nbr = tb.dl_nbr AND t.tr_id = tb.tr_id
WHERE 1=0"""

    def _generate_dynamic_sql(self, variable_pattern: str, tranche_mappings: Dict[str, List[str]], 
                            cycle_code: int, deal_numbers: List[int]) -> str:
        """Generate dynamic SQL for validation purposes (used by validation script)"""
        
        # Build UNION ALL query for all tranche suffixes
        union_parts = []
        
        for tranche_suffix, tr_id_list in tranche_mappings.items():
            variable_name = variable_pattern.replace("{tranche_suffix}", tranche_suffix)
            tr_id_placeholders = "', '".join(tr_id_list)
            deal_placeholders = ", ".join(str(deal) for deal in deal_numbers)
            
            sql_part = f"""
            SELECT 
                cdi.dl_nbr,
                tb.tr_id,
                cdi.cycle_cde,
                CAST(LTRIM(RTRIM(cdi.dl_cdi_var_value)) AS FLOAT) as variable_value,
                '{tranche_suffix}' as tranche_type,
                LTRIM(RTRIM(cdi.dl_cdi_var_nme)) as variable_name
            FROM deal_cdi_var_rpt cdi
            JOIN tranchebal tb ON cdi.dl_nbr = tb.dl_nbr AND cdi.cycle_cde = tb.cycle_cde
            WHERE cdi.dl_nbr IN ({deal_placeholders})
                AND cdi.cycle_cde = {cycle_code}
                AND LTRIM(RTRIM(cdi.dl_cdi_var_nme)) = '{variable_name}'
                AND tb.tr_id IN ('{tr_id_placeholders}')"""
            
            union_parts.append(sql_part)
        
        # Combine all parts with UNION ALL
        full_sql = " UNION ALL ".join(union_parts)
        
        return full_sql
    
    # ===== CONFIGURATION HELPERS =====
    
    def get_available_variable_patterns(self) -> List[str]:
        """Get common CDI variable patterns for UI"""
        return [
            "#RPT_RRI_{tranche_suffix}",    # Investment Income
            "#RPT_EXC_{tranche_suffix}",    # Excess Interest  
            "#RPT_FEES_{tranche_suffix}",   # Fees
            "#RPT_PRINC_{tranche_suffix}",  # Principal
            "#RPT_INT_{tranche_suffix}"     # Interest
        ]
    
    def get_default_tranche_mappings(self) -> Dict[str, List[str]]:
        """Get default tranche mappings based on your existing query"""
        return {
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
    
    # ===== ENHANCED FEATURES WITH MODELS =====
    
    def get_cdi_variable_summary(self, cycle_code: int, deal_numbers: List[int] = None) -> Dict[str, Any]:
        """Get summary statistics for CDI variables using models"""
        
        query = self.dw_db.query(DealCdiVarRpt).filter(
            DealCdiVarRpt.cycle_cde == cycle_code
        )
        
        if deal_numbers:
            query = query.filter(DealCdiVarRpt.dl_nbr.in_(deal_numbers))
        
        cdi_vars = query.all()
        
        # Analyze the data
        summary = {
            "total_variables": len(cdi_vars),
            "unique_deals": len(set(var.dl_nbr for var in cdi_vars)),
            "variable_types": {},
            "value_ranges": {}
        }
        
        # Group by variable type
        for var in cdi_vars:
            var_name = var.variable_name
            if var_name not in summary["variable_types"]:
                summary["variable_types"][var_name] = 0
            summary["variable_types"][var_name] += 1
            
            # Track value ranges
            numeric_val = var.numeric_value
            if var_name not in summary["value_ranges"]:
                summary["value_ranges"][var_name] = {"min": numeric_val, "max": numeric_val, "count": 0}
            else:
                summary["value_ranges"][var_name]["min"] = min(summary["value_ranges"][var_name]["min"], numeric_val)
                summary["value_ranges"][var_name]["max"] = max(summary["value_ranges"][var_name]["max"], numeric_val)
            summary["value_ranges"][var_name]["count"] += 1
        
        return summary