# app/calculations/cdi_service.py - FIXED VERSION SUPPORTING BOTH DEAL AND TRANCHE LEVEL
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
    """Service for managing CDI Variable calculations supporting both deal and tranche level"""
    
    def __init__(self, dw_db: Session, config_db: Session, system_calc_service: SystemCalculationService):
        self.dw_db = dw_db
        self.config_db = config_db
        self.system_calc_service = system_calc_service
    
    # ===== CDI VARIABLE CRUD OPERATIONS =====
    
    def create_cdi_variable_calculation(self, request: CDIVariableCreate, created_by: str) -> CDIVariableResponse:
        """Create a new CDI variable calculation - FIXED to support both deal and tranche level"""
        
        # FIXED: Don't force tranche level - respect the request
        if not hasattr(request, 'group_level') or not request.group_level:
            # Default based on whether tranche mappings are provided
            default_level = GroupLevel.TRANCHE if request.tranche_mappings else GroupLevel.DEAL
        else:
            default_level = GroupLevel(request.group_level)
        
        # Generate the metadata config for CDI variables
        metadata_config = {
            "calculation_type": "cdi_variable",
            "variable_pattern": request.variable_pattern,
            "group_level": default_level.value,  # Store the actual level
            "tranche_mappings": request.tranche_mappings if default_level == GroupLevel.TRANCHE else {},
            "description": f"CDI Variable calculation",
            "required_models": self._get_required_models(default_level),
            "performance_hints": {
                "complexity": "medium",
                "estimated_rows": 1000,
                "uses_orm": True,
                "is_deal_level": default_level == GroupLevel.DEAL
            }
        }
        
        # Create the SystemCalculation
        from .schemas import SystemCalculationCreate
        system_calc_request = SystemCalculationCreate(
            name=request.name,
            description=request.description,
            raw_sql=self._generate_placeholder_sql(request.variable_pattern, default_level),
            result_column_name=request.result_column_name,
            group_level=default_level,  # FIXED: Use the actual level, not hardcoded TRANCHE
            metadata_config=metadata_config
        )
        
        system_calc = self.system_calc_service.create_system_calculation(system_calc_request, created_by)
        
        return CDIVariableResponse(
            id=system_calc.id,
            name=system_calc.name,
            description=system_calc.description,
            variable_pattern=request.variable_pattern,
            result_column_name=system_calc.result_column_name,
            group_level=default_level.value,  # Include group level in response
            tranche_mappings=request.tranche_mappings if default_level == GroupLevel.TRANCHE else {},
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
        all_system_calcs = self.system_calc_service.get_all_system_calculations()
        
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
        if request.tranche_mappings is not None:
            metadata_config["tranche_mappings"] = request.tranche_mappings
        if hasattr(request, 'group_level') and request.group_level:
            metadata_config["group_level"] = request.group_level
        
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
    
    # ===== EXECUTION METHODS SUPPORTING BOTH LEVELS =====
    
    def execute_cdi_variable_calculation(self, calc_id: int, cycle_code: int, 
                                       deal_numbers: List[int]) -> pd.DataFrame:
        """Execute a CDI variable calculation - FIXED to support both deal and tranche level"""
        
        system_calc = self.system_calc_service.get_system_calculation_by_id(calc_id)
        if not system_calc or not self._is_cdi_variable_calculation(system_calc):
            raise CalculationNotFoundError(f"CDI variable calculation with ID {calc_id} not found")
        
        metadata = system_calc.metadata_config
        variable_pattern = metadata["variable_pattern"]
        group_level = GroupLevel(metadata.get("group_level", "tranche"))
        
        try:
            if group_level == GroupLevel.DEAL:
                # DEAL-LEVEL: Query CDI variables directly without tranche join
                result_data = self._execute_deal_level(variable_pattern, cycle_code, deal_numbers)
            else:
                # TRANCHE-LEVEL: Query with tranche mappings (original approach)
                tranche_mappings = metadata["tranche_mappings"]
                result_data = self._execute_tranche_level(variable_pattern, tranche_mappings, cycle_code, deal_numbers)
            
            # Convert to DataFrame
            if result_data:
                result_df = pd.DataFrame(result_data)
                # Ensure consistent column naming
                if 'variable_value' in result_df.columns:
                    result_df = result_df.rename(columns={'variable_value': system_calc.result_column_name})
            else:
                # Return empty DataFrame with expected columns
                base_columns = ['dl_nbr', 'cycle_cde', system_calc.result_column_name]
                if group_level == GroupLevel.TRANCHE:
                    base_columns.insert(1, 'tr_id')
                result_df = pd.DataFrame(columns=base_columns)
            
            return result_df
            
        except Exception as e:
            raise InvalidCalculationError(f"Error executing CDI variable calculation: {str(e)}")
    
    def _execute_deal_level(self, variable_pattern: str, cycle_code: int, deal_numbers: List[int]) -> List[Dict]:
        """Execute deal-level CDI variable calculation (NEW)"""
        
        # For deal-level variables, we don't use tranche suffix replacement
        # The variable pattern should be the exact variable name
        if '{tranche_suffix}' in variable_pattern:
            raise InvalidCalculationError(
                "Deal-level CDI variables should not contain {tranche_suffix} placeholder"
            )
        
        variable_name = variable_pattern
        
        # Query CDI variables directly without tranche join
        cdi_vars = (
            self.dw_db.query(DealCdiVarRpt)
            .filter(
                DealCdiVarRpt.dl_nbr.in_(deal_numbers),
                DealCdiVarRpt.cycle_cde == cycle_code,
                DealCdiVarRpt.dl_cdi_var_nme == variable_name.ljust(32)  # Account for CHAR(32) padding
            )
            .all()
        )
        
        # Convert to result format (no tr_id for deal-level)
        results = []
        for cdi_var in cdi_vars:
            results.append({
                'dl_nbr': cdi_var.dl_nbr,
                'cycle_cde': cdi_var.cycle_cde,
                'variable_value': cdi_var.numeric_value,
                'variable_name': cdi_var.variable_name
            })
        
        return results
    
    def _execute_tranche_level(self, variable_pattern: str, tranche_mappings: Dict[str, List[str]], 
                             cycle_code: int, deal_numbers: List[int]) -> List[Dict]:
        """Execute tranche-level CDI variable calculation with clean trimmed matching"""
        
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
            
            # For each CDI variable found, match it with corresponding tranches using TRIM
            for cdi_var in cdi_vars:
                from sqlalchemy import func
                matching_tranches = (
                    self.dw_db.query(TrancheBal)
                    .filter(
                        TrancheBal.dl_nbr == cdi_var.dl_nbr,
                        TrancheBal.cycle_cde == cdi_var.cycle_cde,
                        func.trim(TrancheBal.tr_id).in_(tr_id_list)  # CLEAN: Always use trimmed matching
                    )
                    .all()
                )
                
                # Create result records for each matching tranche
                for tranche in matching_tranches:
                    all_results.append({
                        'dl_nbr': cdi_var.dl_nbr,
                        'tr_id': tranche.tr_id,  # Keep the original padded tr_id from database
                        'cycle_cde': cdi_var.cycle_cde,
                        'variable_value': cdi_var.numeric_value,
                        'tranche_type': tranche_suffix,
                        'variable_name': cdi_var.variable_name
                    })
        
        return all_results
    
    # ===== DISCOVERY AND VALIDATION METHODS =====
    
    def discover_deal_level_variables(self, cycle_code: int, deal_numbers: List[int] = None, 
                                    pattern_prefix: str = "#RPT_") -> List[Dict[str, Any]]:
        """Discover deal-level CDI variables (NEW)"""
        
        query = self.dw_db.query(
            DealCdiVarRpt.dl_cdi_var_nme.distinct(),
            DealCdiVarRpt.dl_nbr.label('sample_deal')
        ).filter(
            DealCdiVarRpt.cycle_cde == cycle_code,
            DealCdiVarRpt.dl_cdi_var_nme.like(f"{pattern_prefix}%")
        )
        
        if deal_numbers:
            query = query.filter(DealCdiVarRpt.dl_nbr.in_(deal_numbers))
        
        results = query.all()
        
        # Check which variables are deal-level vs tranche-level
        deal_level_vars = []
        
        for var_name, sample_deal in results:
            var_name_clean = var_name.strip()
            
            # Check if this variable appears without corresponding tranche data
            # (i.e., it's truly deal-level)
            tranche_check = (
                self.dw_db.query(DealCdiVarRpt)
                .join(TrancheBal, and_(
                    DealCdiVarRpt.dl_nbr == TrancheBal.dl_nbr,
                    DealCdiVarRpt.cycle_cde == TrancheBal.cycle_cde
                ))
                .filter(
                    DealCdiVarRpt.dl_cdi_var_nme == var_name,
                    DealCdiVarRpt.cycle_cde == cycle_code,
                    DealCdiVarRpt.dl_nbr == sample_deal
                )
                .count()
            )
            
            direct_check = (
                self.dw_db.query(DealCdiVarRpt)
                .filter(
                    DealCdiVarRpt.dl_cdi_var_nme == var_name,
                    DealCdiVarRpt.cycle_cde == cycle_code,
                    DealCdiVarRpt.dl_nbr == sample_deal
                )
                .count()
            )
            
            # If direct query returns more records than tranche join, it's likely deal-level
            is_likely_deal_level = direct_check > 0 and (tranche_check == 0 or direct_check > tranche_check * 2)
            
            if is_likely_deal_level:
                deal_level_vars.append({
                    'variable_name': var_name_clean,
                    'sample_deal': sample_deal,
                    'appears_deal_level': True,
                    'direct_records': direct_check,
                    'tranche_joined_records': tranche_check
                })
        
        return deal_level_vars
    
    def analyze_cdi_variable_level(self, variable_name: str, cycle_code: int, 
                                 deal_numbers: List[int]) -> Dict[str, Any]:
        """Analyze whether a CDI variable is deal-level or tranche-level (NEW)"""
        
        padded_name = variable_name.ljust(32)
        
        # Query direct CDI records
        direct_records = (
            self.dw_db.query(DealCdiVarRpt)
            .filter(
                DealCdiVarRpt.dl_cdi_var_nme == padded_name,
                DealCdiVarRpt.cycle_cde == cycle_code,
                DealCdiVarRpt.dl_nbr.in_(deal_numbers)
            )
            .count()
        )
        
        # Query records that can be joined to tranches
        tranche_joined_records = (
            self.dw_db.query(DealCdiVarRpt)
            .join(TrancheBal, and_(
                DealCdiVarRpt.dl_nbr == TrancheBal.dl_nbr,
                DealCdiVarRpt.cycle_cde == TrancheBal.cycle_cde
            ))
            .filter(
                DealCdiVarRpt.dl_cdi_var_nme == padded_name,
                DealCdiVarRpt.cycle_cde == cycle_code,
                DealCdiVarRpt.dl_nbr.in_(deal_numbers)
            )
            .count()
        )
        
        # Analyze the pattern
        if direct_records == 0:
            level_suggestion = "no_data"
        elif tranche_joined_records == 0:
            level_suggestion = "deal_level"
        elif direct_records == tranche_joined_records:
            level_suggestion = "tranche_level" 
        elif direct_records > tranche_joined_records:
            level_suggestion = "mixed_or_deal_level"
        else:
            level_suggestion = "unknown"
        
        return {
            'variable_name': variable_name,
            'direct_records': direct_records,
            'tranche_joined_records': tranche_joined_records,
            'suggested_level': level_suggestion,
            'analysis': {
                'has_data': direct_records > 0,
                'can_join_tranches': tranche_joined_records > 0,
                'ratio': direct_records / max(tranche_joined_records, 1)
            }
        }

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
    
    def _get_required_models(self, group_level: GroupLevel) -> List[str]:
        """Get required models based on group level"""
        if group_level == GroupLevel.DEAL:
            return ["Deal", "DealCdiVarRpt"]
        else:
            return ["Deal", "TrancheBal", "DealCdiVarRpt"]
    
    def _generate_placeholder_sql(self, variable_pattern: str, group_level: GroupLevel) -> str:
        """Generate placeholder SQL for SystemCalculation storage"""
        if group_level == GroupLevel.DEAL:
            return f"""SELECT 
                dl_nbr,
                cycle_cde,
                0.0 as calculated_value
            FROM dbo.deal_cdi_var_rpt 
            WHERE 1=0"""
        else:
            return f"""SELECT 
                dl_nbr,
                'placeholder' as tr_id, 
                cycle_cde,
                0.0 as calculated_value
            FROM dbo.deal_cdi_var_rpt 
            WHERE 1=0"""
    
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
            result_column_name=system_calc.result_column_name,
            group_level=metadata.get("group_level", "tranche"),  # Include group level
            tranche_mappings=metadata.get("tranche_mappings", {}),
            created_by=system_calc.created_by,
            created_at=system_calc.created_at,
            is_active=system_calc.is_active
        )

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

    # ===== SQL PREVIEW GENERATION =====
    
    def generate_cdi_sql_preview(self, calc_id: int, cycle_code: int, deal_numbers: List[int]) -> Dict[str, Any]:
        """Generate SQL preview for CDI variable calculation"""
        
        system_calc = self.system_calc_service.get_system_calculation_by_id(calc_id)
        if not system_calc or not self._is_cdi_variable_calculation(system_calc):
            raise CalculationNotFoundError(f"CDI variable calculation with ID {calc_id} not found")
        
        metadata = system_calc.metadata_config
        variable_pattern = metadata["variable_pattern"]
        group_level = GroupLevel(metadata.get("group_level", "tranche"))
        
        if group_level == GroupLevel.DEAL:
            return self._generate_deal_level_sql_preview(variable_pattern, cycle_code, deal_numbers)
        else:
            tranche_mappings = metadata["tranche_mappings"]
            return self._generate_tranche_level_sql_preview(variable_pattern, tranche_mappings, cycle_code, deal_numbers)
    
    def _generate_deal_level_sql_preview(self, variable_pattern: str, cycle_code: int, deal_numbers: List[int]) -> Dict[str, Any]:
        """Generate SQL preview for deal-level CDI calculation"""
        
        # For deal-level, the pattern should be the exact variable name
        variable_name = variable_pattern
        
        sql = f"""-- Deal-level CDI Variable Query
-- Variable Pattern: {variable_pattern}
-- Variable Name: {variable_name}

SELECT 
    cdi.dl_nbr as "Deal Number",
    cdi.cycle_cde as "Cycle Code", 
    cdi.dl_cdi_var_value as variable_value,
    TRIM(cdi.dl_cdi_var_nme) as variable_name
FROM dbo.deal_cdi_var_rpt cdi
WHERE cdi.dl_nbr IN ({', '.join(map(str, deal_numbers))})
    AND cdi.cycle_cde = {cycle_code}
    AND TRIM(cdi.dl_cdi_var_nme) = '{variable_name}'
ORDER BY cdi.dl_nbr"""

        return {
            "sql": sql,
            "calculation_type": "deal_level_cdi",
            "variable_pattern": variable_pattern,
            "variable_name": variable_name,
            "estimated_rows": len(deal_numbers)
        }
    
    def _generate_tranche_level_sql_preview(self, variable_pattern: str, tranche_mappings: Dict[str, List[str]], 
                                          cycle_code: int, deal_numbers: List[int]) -> Dict[str, Any]:
        """Generate SQL preview for tranche-level CDI calculation"""
        
        # Generate individual queries for each tranche suffix
        union_queries = []
        variable_names = []
        
        for tranche_suffix, tr_id_list in tranche_mappings.items():
            variable_name = variable_pattern.replace("{tranche_suffix}", tranche_suffix)
            variable_names.append(variable_name)
            
            tr_id_filter = "', '".join(tr_id_list)
            
            query = f"""    -- Tranche Suffix: {tranche_suffix} -> Variable: {variable_name}
    SELECT 
        cdi.dl_nbr as "Deal Number",
        tb.tr_id as "Tranche ID",
        cdi.cycle_cde as "Cycle Code",
        cdi.dl_cdi_var_value as variable_value,
        TRIM(cdi.dl_cdi_var_nme) as variable_name,
        '{tranche_suffix}' as tranche_type
    FROM dbo.deal_cdi_var_rpt cdi
    INNER JOIN dbo.tranchebal tb ON cdi.dl_nbr = tb.dl_nbr 
        AND cdi.cycle_cde = tb.cycle_cde
    WHERE cdi.dl_nbr IN ({', '.join(map(str, deal_numbers))})
        AND cdi.cycle_cde = {cycle_code}
        AND TRIM(cdi.dl_cdi_var_nme) = '{variable_name}'
        AND tb.tr_id IN ('{tr_id_filter}')"""
            
            union_queries.append(query)
        
        # Combine all queries with UNION ALL
        sql = f"""-- Tranche-level CDI Variable Query
-- Variable Pattern: {variable_pattern}
-- Tranche Mappings: {len(tranche_mappings)} suffix mappings

{chr(10).join(union_queries)}

UNION ALL

""".rstrip("UNION ALL\n\n") + """
ORDER BY "Deal Number", "Tranche ID" """

        estimated_rows = len(deal_numbers) * sum(len(tr_ids) for tr_ids in tranche_mappings.values())
        
        return {
            "sql": sql,
            "calculation_type": "tranche_level_cdi", 
            "variable_pattern": variable_pattern,
            "variable_names": variable_names,
            "tranche_mappings": tranche_mappings,
            "estimated_rows": estimated_rows
        }