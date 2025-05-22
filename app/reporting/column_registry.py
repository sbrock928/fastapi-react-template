"""Column registry for dynamic report building."""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from decimal import Decimal


class ColumnType(str, Enum):
    """Types of columns available."""
    BASIC = "basic"           # Direct field from model
    CALCULATED = "calculated" # Computed field
    AGGREGATED = "aggregated" # Aggregation across tranches


class ColumnScope(str, Enum):
    """Which report scopes support this column."""
    DEAL = "DEAL"
    TRANCHE = "TRANCHE"
    BOTH = "BOTH"


class ColumnDefinition:
    """Definition of a reportable column."""
    
    def __init__(
        self,
        key: str,
        label: str,
        description: str,
        column_type: ColumnType,
        scope: ColumnScope,
        data_type: str = "string",
        formatter: Optional[str] = None,
        calculation_func: Optional[Callable] = None,
        is_default: bool = False,
        category: str = "General",
        sort_order: int = 0
    ):
        self.key = key
        self.label = label
        self.description = description
        self.column_type = column_type
        self.scope = scope
        self.data_type = data_type  # string, number, currency, percentage, date
        self.formatter = formatter
        self.calculation_func = calculation_func
        self.is_default = is_default
        self.category = category
        self.sort_order = sort_order


# Column Registry
COLUMN_REGISTRY: Dict[str, ColumnDefinition] = {}


def register_column(definition: ColumnDefinition):
    """Register a column definition."""
    COLUMN_REGISTRY[definition.key] = definition


def get_available_columns(scope: ColumnScope) -> List[ColumnDefinition]:
    """Get columns available for a specific scope."""
    return [
        col for col in COLUMN_REGISTRY.values()
        if col.scope == scope or col.scope == ColumnScope.BOTH
    ]


def get_default_columns(scope: ColumnScope) -> List[str]:
    """Get default column keys for a scope."""
    return [
        col.key for col in get_available_columns(scope)
        if col.is_default
    ]


# Register Deal-level columns
register_column(ColumnDefinition(
    key="deal_id",
    label="Deal ID",
    description="Unique identifier for the deal",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="number",
    category="Identification",
    sort_order=1
))

register_column(ColumnDefinition(
    key="deal_name",
    label="Deal Name",
    description="Name of the deal",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="string",
    is_default=True,
    category="Identification",
    sort_order=2
))

register_column(ColumnDefinition(
    key="originator",
    label="Originator",
    description="Institution that originated the deal",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="string",
    is_default=True,
    category="Deal Information",
    sort_order=3
))

register_column(ColumnDefinition(
    key="deal_type",
    label="Deal Type",
    description="Type of securitization (RMBS, CMBS, etc.)",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="string",
    is_default=True,
    category="Deal Information",
    sort_order=4
))

register_column(ColumnDefinition(
    key="total_principal",
    label="Total Principal",
    description="Total principal amount of the deal",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="currency",
    is_default=True,
    category="Financial",
    sort_order=5
))

register_column(ColumnDefinition(
    key="credit_rating",
    label="Credit Rating",
    description="Credit rating of the deal",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="string",
    is_default=True,
    category="Risk",
    sort_order=6
))

register_column(ColumnDefinition(
    key="yield_rate",
    label="Yield Rate",
    description="Expected yield rate of the deal",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="percentage",
    is_default=True,
    category="Financial",
    sort_order=7
))

register_column(ColumnDefinition(
    key="closing_date",
    label="Closing Date",
    description="Date when the deal was closed",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="date",
    category="Dates",
    sort_order=8
))

register_column(ColumnDefinition(
    key="duration",
    label="Duration",
    description="Duration of the deal in years",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.DEAL,
    data_type="number",
    category="Financial",
    sort_order=9
))

# Tranche-specific columns
register_column(ColumnDefinition(
    key="tranche_id",
    label="Tranche ID",
    description="Unique identifier for the tranche",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="number",
    category="Identification",
    sort_order=10
))

register_column(ColumnDefinition(
    key="tranche_name",
    label="Tranche Name",
    description="Name of the tranche",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="string",
    is_default=True,
    category="Identification",
    sort_order=11
))

register_column(ColumnDefinition(
    key="class_name",
    label="Class",
    description="Tranche class (A, B, C, etc.)",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="string",
    is_default=True,
    category="Tranche Information",
    sort_order=12
))

register_column(ColumnDefinition(
    key="principal_amount",
    label="Principal Amount",
    description="Principal amount of the tranche",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="currency",
    is_default=True,
    category="Financial",
    sort_order=13
))

register_column(ColumnDefinition(
    key="interest_rate",
    label="Interest Rate",
    description="Interest rate of the tranche",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="percentage",
    is_default=True,
    category="Financial",
    sort_order=14
))

register_column(ColumnDefinition(
    key="payment_priority",
    label="Payment Priority",
    description="Payment priority in the waterfall",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="number",
    category="Tranche Information",
    sort_order=15
))

register_column(ColumnDefinition(
    key="subordination_level",
    label="Subordination Level",
    description="Level of subordination (1=Senior, 2=Mezzanine, 3=Subordinate)",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="number",
    category="Risk",
    sort_order=16
))

register_column(ColumnDefinition(
    key="maturity_date",
    label="Maturity Date",
    description="Maturity date of the tranche",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.TRANCHE,
    data_type="date",
    category="Dates",
    sort_order=17
))

# Calculated/Aggregated columns for Deal-level reports
register_column(ColumnDefinition(
    key="tranche_count",
    label="Tranche Count",
    description="Number of tranches in the deal",
    column_type=ColumnType.AGGREGATED,
    scope=ColumnScope.DEAL,
    data_type="number",
    category="Aggregations",
    sort_order=18
))

register_column(ColumnDefinition(
    key="total_tranche_principal",
    label="Total Tranche Principal",
    description="Sum of all tranche principal amounts",
    column_type=ColumnType.AGGREGATED,
    scope=ColumnScope.DEAL,
    data_type="currency",
    category="Aggregations",
    sort_order=19
))

register_column(ColumnDefinition(
    key="avg_tranche_interest_rate",
    label="Avg Tranche Interest Rate",
    description="Average interest rate across all tranches",
    column_type=ColumnType.AGGREGATED,
    scope=ColumnScope.DEAL,
    data_type="percentage",
    category="Aggregations",
    sort_order=20
))

register_column(ColumnDefinition(
    key="weighted_avg_interest_rate",
    label="Weighted Avg Interest Rate",
    description="Principal-weighted average interest rate",
    column_type=ColumnType.CALCULATED,
    scope=ColumnScope.DEAL,
    data_type="percentage",
    category="Calculations",
    sort_order=21
))

register_column(ColumnDefinition(
    key="senior_tranche_count",
    label="Senior Tranche Count",
    description="Number of senior tranches",
    column_type=ColumnType.AGGREGATED,
    scope=ColumnScope.DEAL,
    data_type="number",
    category="Risk Analysis",
    sort_order=22
))

register_column(ColumnDefinition(
    key="subordinate_tranche_count",
    label="Subordinate Tranche Count",
    description="Number of subordinate tranches",
    column_type=ColumnType.AGGREGATED,
    scope=ColumnScope.DEAL,
    data_type="number",
    category="Risk Analysis",
    sort_order=23
))

# Calculated fields for both scopes
register_column(ColumnDefinition(
    key="cycle_code",
    label="Cycle Code",
    description="Reporting cycle code",
    column_type=ColumnType.BASIC,
    scope=ColumnScope.BOTH,
    data_type="string",
    category="Metadata",
    sort_order=24
))

register_column(ColumnDefinition(
    key="days_since_closing",
    label="Days Since Closing",
    description="Number of days since deal closing",
    column_type=ColumnType.CALCULATED,
    scope=ColumnScope.BOTH,
    data_type="number",
    category="Calculations",
    sort_order=25
))


def get_columns_by_category(scope: ColumnScope) -> Dict[str, List[ColumnDefinition]]:
    """Get columns grouped by category for a specific scope."""
    columns = get_available_columns(scope)
    categories = {}
    
    for col in sorted(columns, key=lambda x: (x.category, x.sort_order)):
        if col.category not in categories:
            categories[col.category] = []
        categories[col.category].append(col)
    
    return categories