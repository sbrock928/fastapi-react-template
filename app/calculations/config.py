# app/calculations/config.py
"""Dynamic calculation configuration generator using SQLAlchemy model inspection."""

from sqlalchemy import inspect
from typing import Dict, List, Any, Optional
from app.datawarehouse.models import Deal, Tranche, TrancheBal


class CalculationConfigGenerator:
    """Dynamically generate calculation configuration from SQLAlchemy models."""
    
    def __init__(self):
        # Registry of models to expose for calculations
        self.model_registry = {
            "Deal": {
                "model": Deal,
                "label": "Deal",
                "description": "Base deal information",
                "exposed_fields": ["dl_nbr", "issr_cde", "cdi_file_nme", "CDB_cdi_file_nme"],
                "field_descriptions": {
                    "dl_nbr": "Unique identifier for the deal",
                    "issr_cde": "Deal issuer code",
                    "cdi_file_nme": "CDI file name",
                    "CDB_cdi_file_nme": "CDB CDI file name"
                }
            },
            "Tranche": {
                "model": Tranche,
                "label": "Tranche",
                "description": "Tranche structure data",
                "exposed_fields": ["tr_id", "dl_nbr", "tr_cusip_id"],
                "field_descriptions": {
                    "tr_id": "Tranche identifier within the deal",
                    "dl_nbr": "Parent deal number",
                    "tr_cusip_id": "CUSIP identifier for the tranche"
                }
            },
            "TrancheBal": {
                "model": TrancheBal,
                "label": "TrancheBal",
                "description": "Tranche balance and performance data",
                "exposed_fields": [
                    "tr_end_bal_amt", "tr_prin_rel_ls_amt", "tr_pass_thru_rte",
                    "tr_accrl_days", "tr_int_dstrb_amt", "tr_prin_dstrb_amt",
                    "tr_int_accrl_amt", "tr_int_shtfl_amt", "cycle_cde"
                ],
                "field_descriptions": {
                    "tr_end_bal_amt": "Outstanding principal balance at period end",
                    "tr_prin_rel_ls_amt": "Principal released or lost during the period",
                    "tr_pass_thru_rte": "Interest rate passed through to investors",
                    "tr_accrl_days": "Number of days in the accrual period",
                    "tr_int_dstrb_amt": "Interest distributed to investors",
                    "tr_prin_dstrb_amt": "Principal distributed to investors",
                    "tr_int_accrl_amt": "Interest accrued during the period",
                    "tr_int_shtfl_amt": "Interest shortfall amount",
                    "cycle_cde": "Reporting cycle identifier (YYYYMM format)"
                }
            }
        }
        
        # Type mapping from SQLAlchemy to frontend types
        self.type_mapping = {
            'Integer': 'number',
            'String': 'string',
            'CHAR': 'string',
            'Float': 'number',
            'Numeric': 'currency',  # Default for Numeric columns
            'MONEY': 'currency',
            'Boolean': 'boolean',
            'DateTime': 'datetime',
            'Date': 'date',
            'SmallInteger': 'number'
        }
        
        # Field-specific type overrides based on naming patterns or business logic
        self.field_type_overrides = {
            # Rate fields should be percentage
            'tr_pass_thru_rte': 'percentage',
            # All amount fields should be currency
            'tr_end_bal_amt': 'currency',
            'tr_prin_rel_ls_amt': 'currency',
            'tr_int_dstrb_amt': 'currency',
            'tr_prin_dstrb_amt': 'currency',
            'tr_int_accrl_amt': 'currency',
            'tr_int_shtfl_amt': 'currency',
            # Cycle code is a special number format
            'cycle_cde': 'number',
            # Days are always numbers
            'tr_accrl_days': 'number'
        }

    def _get_sqlalchemy_type_name(self, column) -> str:
        """Get the SQLAlchemy type name from a column."""
        return column.type.__class__.__name__

    def _determine_field_type(self, column_name: str, sqlalchemy_type: str) -> str:
        """Determine the frontend field type from SQLAlchemy column."""
        # Check for specific field overrides first
        if column_name in self.field_type_overrides:
            return self.field_type_overrides[column_name]
        
        # Auto-detect based on naming patterns
        if '_amt' in column_name.lower() or 'amount' in column_name.lower():
            return 'currency'
        elif '_rte' in column_name.lower() or 'rate' in column_name.lower():
            return 'percentage'
        elif '_pct' in column_name.lower() or 'percent' in column_name.lower():
            return 'percentage'
        
        # Use general type mapping
        return self.type_mapping.get(sqlalchemy_type, 'string')

    def generate_field_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate field mappings dynamically from SQLAlchemy models."""
        field_mappings = {}
        
        for model_name, config in self.model_registry.items():
            model_class = config["model"]
            inspector = inspect(model_class)
            
            fields = []
            for column_name in config["exposed_fields"]:
                if column_name in inspector.columns:
                    column = inspector.columns[column_name]
                    sqlalchemy_type = self._get_sqlalchemy_type_name(column)
                    field_type = self._determine_field_type(column_name, sqlalchemy_type)
                    
                    # Generate user-friendly label if not provided
                    default_label = column_name.replace('_', ' ').title()
                    custom_label = config["field_descriptions"].get(column_name + "_label", default_label)
                    
                    field_data = {
                        "value": column_name,
                        "label": custom_label,
                        "type": field_type,
                        "description": config["field_descriptions"].get(column_name, f"{custom_label} field"),
                        "nullable": column.nullable,
                        "sqlalchemy_type": sqlalchemy_type
                    }
                    fields.append(field_data)
                else:
                    print(f"Warning: Column '{column_name}' not found in model '{model_name}'")
            
            field_mappings[model_name] = fields
        
        return field_mappings

    def generate_source_models(self) -> List[Dict[str, str]]:
        """Generate source models configuration."""
        return [
            {
                "value": model_name,
                "label": config["label"],
                "description": config["description"]
            }
            for model_name, config in self.model_registry.items()
        ]

    def generate_aggregation_functions(self) -> List[Dict[str, str]]:
        """Generate aggregation functions configuration."""
        return [
            {
                "value": "SUM",
                "label": "SUM - Total amount",
                "description": "Add all values together",
                "category": "aggregated"
            },
            {
                "value": "AVG",
                "label": "AVG - Average",
                "description": "Calculate average value",
                "category": "aggregated"
            },
            {
                "value": "COUNT",
                "label": "COUNT - Count records",
                "description": "Count number of records",
                "category": "aggregated"
            },
            {
                "value": "MIN",
                "label": "MIN - Minimum value",
                "description": "Find minimum value",
                "category": "aggregated"
            },
            {
                "value": "MAX",
                "label": "MAX - Maximum value",
                "description": "Find maximum value",
                "category": "aggregated"
            },
            {
                "value": "WEIGHTED_AVG",
                "label": "WEIGHTED_AVG - Weighted average",
                "description": "Calculate weighted average using specified weight field",
                "category": "aggregated"
            },
            {
                "value": "RAW",
                "label": "RAW - Raw field value",
                "description": "Include field value without aggregation",
                "category": "raw"
            }
        ]

    def generate_group_levels(self) -> List[Dict[str, str]]:
        """Generate group levels configuration."""
        return [
            {
                "value": "deal",
                "label": "Deal Level",
                "description": "Aggregate to deal level"
            },
            {
                "value": "tranche",
                "label": "Tranche Level",
                "description": "Aggregate to tranche level"
            }
        ]

    def generate_full_configuration(self) -> Dict[str, Any]:
        """Generate complete calculation configuration."""
        return {
            "aggregation_functions": self.generate_aggregation_functions(),
            "source_models": self.generate_source_models(),
            "group_levels": self.generate_group_levels(),
            "field_mappings": self.generate_field_mappings()
        }

    def add_model(self, model_name: str, model_class, label: str, description: str, 
                  exposed_fields: List[str], field_descriptions: Optional[Dict[str, str]] = None):
        """Add a new model to the registry dynamically."""
        self.model_registry[model_name] = {
            "model": model_class,
            "label": label,
            "description": description,
            "exposed_fields": exposed_fields,
            "field_descriptions": field_descriptions or {}
        }

    def add_field_to_model(self, model_name: str, field_name: str, description: Optional[str] = None):
        """Add a new field to an existing model."""
        if model_name in self.model_registry:
            if field_name not in self.model_registry[model_name]["exposed_fields"]:
                self.model_registry[model_name]["exposed_fields"].append(field_name)
            if description:
                self.model_registry[model_name]["field_descriptions"][field_name] = description

    def get_model_fields(self, model_name: str) -> List[str]:
        """Get all available fields for a model (for debugging/introspection)."""
        if model_name in self.model_registry:
            model_class = self.model_registry[model_name]["model"]
            inspector = inspect(model_class)
            return list(inspector.columns.keys())
        return []


# Global instance
calculation_config_generator = CalculationConfigGenerator()


# Convenience function for easy access
def get_calculation_configuration() -> Dict[str, Any]:
    """Get the complete calculation configuration."""
    return calculation_config_generator.generate_full_configuration()