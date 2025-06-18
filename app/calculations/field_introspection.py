"""
Dynamic field introspection service for generating available fields from SQLAlchemy models.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy import Integer, String, Float, Numeric, SmallInteger, DateTime, CHAR, LargeBinary
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.inspection import inspect
from app.datawarehouse.models import Deal, Tranche, TrancheBal


class FieldIntrospectionService:
    """Service for dynamically generating field information from SQLAlchemy models"""
    
    # Model mapping for field path generation - LIMITED TO SPECIFIED MODELS ONLY
    MODEL_MAPPING = {
        "deal": Deal,
        "tranche": Tranche,
        "tranchebal": TrancheBal
    }
    
    # Model dependencies - which models are required for each table
    MODEL_DEPENDENCIES = {
        "deal": ["Deal"],
        "tranche": ["Deal", "Tranche"],
        "tranchebal": ["Deal", "Tranche", "TrancheBal"]
    }
    
    # Human-readable names for models
    MODEL_DISPLAY_NAMES = {
        "deal": "Deal",
        "tranche": "Tranche", 
        "tranchebal": "Tranche Balance"
    }

    @classmethod
    def _get_sqlalchemy_type_info(cls, column) -> Dict[str, Any]:
        """Convert SQLAlchemy column type to field type information"""
        column_type = column.type
        
        # Handle different SQLAlchemy types
        if isinstance(column_type, (Integer, SmallInteger)):
            return {"type": "number", "format": "integer"}
        elif isinstance(column_type, (Float, Numeric)):
            # Check if it's a currency field based on name patterns
            if any(term in column.name.lower() for term in ["amt", "amount", "bal", "balance", "price", "value"]):
                return {"type": "currency", "format": "decimal"}
            # Check if it's a rate/percentage field
            elif any(term in column.name.lower() for term in ["rte", "rate", "pct", "percent"]):
                return {"type": "percentage", "format": "decimal"}
            else:
                return {"type": "number", "format": "decimal"}
        elif isinstance(column_type, (String, CHAR)):
            return {"type": "string", "format": "text"}
        elif isinstance(column_type, DateTime):
            return {"type": "datetime", "format": "datetime"}
        elif isinstance(column_type, LargeBinary):
            return {"type": "binary", "format": "binary"}
        else:
            return {"type": "string", "format": "text"}  # Default fallback

    @classmethod
    def _generate_field_description(cls, model_name: str, column_name: str, column) -> str:
        """Generate human-readable description for a field"""
        model_display = cls.MODEL_DISPLAY_NAMES.get(model_name, model_name.title())
        
        # Special cases for known fields
        description_map = {
            "dl_nbr": "Deal number - unique identifier for the deal",
            "tr_id": "Tranche identifier within the deal",
            "cycle_cde": "Reporting cycle identifier (YYYYMM format)",
            "issr_cde": "Deal issuer code",
            "cdi_file_nme": "CDI file name",
            "CDB_cdi_file_nme": "CDB CDI file name",
            "tr_cusip_id": "CUSIP identifier for the tranche",
            "tr_end_bal_amt": "Outstanding principal balance at period end",
            "tr_pass_thru_rte": "Interest rate passed through to investors",
            "tr_prin_rel_ls_amt": "Principal release/loss amount",
            "tr_accrl_days": "Number of accrual days in the period",
            "tr_int_dstrb_amt": "Interest distribution amount",
            "tr_prin_dstrb_amt": "Principal distribution amount",
            "tr_int_accrl_amt": "Interest accrual amount",
            "tr_int_shtfl_amt": "Interest shortfall amount"
        }
        
        if column_name in description_map:
            return description_map[column_name]
        
        # Generate description based on column name and model
        formatted_name = column_name.replace("_", " ").title()
        return f"{formatted_name} from {model_display}"

    @classmethod
    def get_available_fields(cls, model_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate available fields from SQLAlchemy models through introspection
        
        Args:
            model_filter: Optional filter to only include fields from specific model(s)
            
        Returns:
            List of field dictionaries with metadata
        """
        fields = []
        
        for model_key, model_class in cls.MODEL_MAPPING.items():
            # Skip if model filter is specified and doesn't match
            if model_filter and model_key != model_filter.lower():
                continue
                
            # Use SQLAlchemy inspection to get column information
            inspector = inspect(model_class)
            
            for column_name, column in inspector.columns.items():
                # Get type information
                type_info = cls._get_sqlalchemy_type_info(column)
                
                # Build field path
                field_path = f"{model_key}.{column_name}"
                
                # Generate description
                description = cls._generate_field_description(model_key, column_name, column)
                
                # Create field entry with the exact format expected by frontend
                field_entry = {
                    "value": field_path,  # Frontend expects 'value' not 'field_path'
                    "label": f"{column_name.replace('_', ' ').title()} ({field_path})",  # Frontend expects 'label'
                    "field_path": field_path,  # Keep this for backward compatibility
                    "name": column_name.replace("_", " ").title(),
                    "description": description,
                    "type": type_info["type"],
                    "format": type_info.get("format"),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "foreign_key": bool(column.foreign_keys),
                    "required_models": cls.MODEL_DEPENDENCIES.get(model_key, [model_key.title()]),
                    "model": model_key,
                    "model_display_name": cls.MODEL_DISPLAY_NAMES.get(model_key, model_key.title())
                }
                
                fields.append(field_entry)
        
        # Sort fields by model, then by field name
        fields.sort(key=lambda x: (x["model"], x["field_path"]))
        
        return fields

    @classmethod
    def get_fields_by_model(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get fields grouped by model"""
        all_fields = cls.get_available_fields()
        
        grouped = {}
        for field in all_fields:
            model_key = field["model"]
            if model_key not in grouped:
                grouped[model_key] = []
            grouped[model_key].append(field)
        
        return grouped

    @classmethod
    def get_field_by_path(cls, field_path: str) -> Optional[Dict[str, Any]]:
        """Get field information by field path"""
        try:
            model_key, column_name = field_path.split(".", 1)
            fields = cls.get_available_fields(model_filter=model_key)
            
            for field in fields:
                if field["field_path"] == field_path:
                    return field
            
            return None
        except ValueError:
            return None

    @classmethod
    def validate_field_path(cls, field_path: str) -> Dict[str, Any]:
        """Validate if a field path exists and return validation result"""
        field = cls.get_field_by_path(field_path)
        
        if field:
            return {
                "is_valid": True,
                "field": field,
                "message": f"Field '{field_path}' is valid"
            }
        else:
            return {
                "is_valid": False,
                "field": None,
                "message": f"Field '{field_path}' not found"
            }

    @classmethod
    def get_available_models(cls) -> List[Dict[str, Any]]:
        """Get available models for selection"""
        models = []
        
        # Map lowercase keys to proper case values that match SourceModel enum
        model_value_mapping = {
            "deal": "Deal",
            "tranche": "Tranche", 
            "tranchebal": "TrancheBal"
        }
        
        for model_key, model_class in cls.MODEL_MAPPING.items():
            models.append({
                "value": model_value_mapping.get(model_key, model_key.title()),  # Use proper case
                "label": cls.MODEL_DISPLAY_NAMES.get(model_key, model_key.title()),
                "description": model_class.__doc__ or f"{model_key.title()} data model",
                "table_name": model_class.__tablename__,
                "dependencies": cls.MODEL_DEPENDENCIES.get(model_key, [])
            })
        
        return models