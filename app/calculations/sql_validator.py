# app/calculations/sql_validator.py
"""SQL validation system for custom SQL calculations."""

import re
import sqlparse
from sqlparse import sql, tokens
from typing import List, Set, Dict, Optional, Tuple
from pydantic import BaseModel, validator
from enum import Enum


class SQLValidationError(Exception):
    """Custom exception for SQL validation errors."""

    pass


class RequiredField(BaseModel):
    """Represents a required field for group level validation."""

    table: str
    column: str
    alias: Optional[str] = None

    def matches_column(self, column_text: str, table_aliases: Dict[str, str] = None) -> bool:
        """Check if a column text matches this required field."""
        column_lower = column_text.lower().strip()
        table_aliases = table_aliases or {}

        # Direct match: table.column
        if f"{self.table}.{self.column}" in column_lower:
            return True

        # Check with table aliases
        for alias, real_table in table_aliases.items():
            if real_table.lower() == self.table.lower():
                if f"{alias}.{self.column}" in column_lower:
                    return True

        # Check for just column name if it's unambiguous
        if f".{self.column}" in column_lower or column_lower.endswith(self.column):
            return True

        return False


class GroupLevelRequirements(BaseModel):
    """Requirements for different group levels."""

    deal_level: List[RequiredField] = [RequiredField(table="deal", column="dl_nbr")]
    tranche_level: List[RequiredField] = [
        RequiredField(table="deal", column="dl_nbr"),
        RequiredField(table="tranche", column="tr_id"),
    ]


class SQLValidationResult(BaseModel):
    """Result of SQL validation."""

    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    extracted_columns: List[str] = []
    detected_tables: Set[str] = set()
    table_aliases: Dict[str, str] = {}
    result_column_name: Optional[str] = None


class CustomSQLValidator:
    """Validates custom SQL for system calculations."""

    def __init__(self):
        self.requirements = GroupLevelRequirements()
        # Enhanced dangerous patterns - more comprehensive detection
        self.dangerous_patterns = [
            # DDL Operations - catch any context
            r"(?i)\bdrop\b",  # Any DROP statement
            r"(?i)\bdelete\s+from\b",
            r"(?i)\binsert\s+into\b",
            r"(?i)\bupdate\s+.*\bset\b",
            r"(?i)\balter\s+table\b",
            r"(?i)\bcreate\s+table\b",
            r"(?i)\btruncate\s+table\b",
            # Execution commands
            r"(?i)\bexec\s*\(",
            r"(?i)\bexecute\s*\(",
            r"(?i)\bsp_\w+",  # Stored procedures
            r"(?i)\bxp_\w+",  # Extended procedures
            # Security risks
            r"(?i)--",  # SQL comments
            r"(?i)/\*.*\*/",  # Block comments
            r"(?i)\bunion\s+select",  # Prevent SQL injection via UNION
            r"(?i)\binto\s+outfile\b",  # File operations
            r"(?i)\bload_file\s*\(",  # File reading
            r"(?i)\bload\s+data\b",  # Data loading
            # System functions
            r"(?i)\buser\s*\(\s*\)",  # USER() function
            r"(?i)\bdatabase\s*\(\s*\)",  # DATABASE() function
            r"(?i)\bversion\s*\(\s*\)",  # VERSION() function
            r"(?i)\b@@\w+",  # System variables
            # Dangerous keywords in any context
            r"(?i)\bgrant\b",
            r"(?i)\brevoke\b",
            r"(?i)\bshutdown\b",
        ]

        # Keywords that should never appear in SELECT statements
        self.forbidden_keywords = [
            "drop",
            "delete",
            "insert",
            "update",
            "alter",
            "create",
            "truncate",
            "grant",
            "revoke",
            "shutdown",
            "exec",
            "execute",
        ]

    def validate_custom_sql(
        self, sql_text: str, group_level: str, expected_result_column: str
    ) -> SQLValidationResult:
        """
        Comprehensive validation of custom SQL for system calculations.

        Args:
            sql_text: The SQL to validate
            group_level: 'deal' or 'tranche'
            expected_result_column: Expected name of the result column

        Returns:
            SQLValidationResult with validation status and details
        """
        result = SQLValidationResult(is_valid=True)

        try:
            # 1. Basic security validation
            self._validate_security(sql_text, result)

            # 2. Parse SQL structure
            parsed = sqlparse.parse(sql_text)
            if not parsed:
                result.errors.append("Invalid SQL syntax - could not parse")
                result.is_valid = False
                return result

            statement = parsed[0]

            # 3. Validate it's a SELECT statement
            self._validate_select_statement(statement, result)

            # 4. Extract table aliases
            self._extract_table_aliases(statement, result)

            # 5. Extract and validate SELECT columns
            self._extract_select_columns(statement, result)

            # 6. Validate required fields for group level are in SELECT
            self._validate_required_fields_in_select(statement, group_level, result)

            # 7. Validate result column
            self._validate_result_column(expected_result_column, result)

            # 8. Extract table references
            self._extract_table_references(statement, result)

            # 9. Additional structural validation
            self._validate_sql_structure(statement, result)

        except Exception as e:
            result.errors.append(f"SQL parsing error: {str(e)}")
            result.is_valid = False

        # Final validation
        result.is_valid = len(result.errors) == 0
        return result

    def _validate_security(self, sql_text: str, result: SQLValidationResult) -> None:
        """Check for dangerous SQL patterns."""
        for pattern in self.dangerous_patterns:
            if re.search(pattern, sql_text):
                # Extract the matched pattern for better error reporting
                match = re.search(pattern, sql_text)
                if match:
                    matched_text = match.group(0)
                    result.errors.append(
                        f"Dangerous SQL pattern detected: '{matched_text}' - this operation is not allowed in custom calculations"
                    )
                else:
                    result.errors.append(
                        f"Dangerous SQL pattern detected - this operation is not allowed in custom calculations"
                    )

        # Additional check: forbidden keywords should not appear in SELECT clause
        self._validate_forbidden_keywords_in_select(sql_text, result)

        # Check for multiple statements (should be single SELECT)
        statements = sqlparse.split(sql_text)
        if len(statements) > 1:
            result.errors.append(
                "Multiple SQL statements not allowed - only single SELECT statements permitted"
            )

        # Check for suspicious keywords
        suspicious_keywords = ["xp_", "sp_", "fn_", "bulk", "openquery", "openrowset"]
        sql_lower = sql_text.lower()
        for keyword in suspicious_keywords:
            if keyword in sql_lower:
                result.warnings.append(f"Potentially dangerous keyword detected: {keyword}")

    def _validate_forbidden_keywords_in_select(
        self, sql_text: str, result: SQLValidationResult
    ) -> None:
        """Check for forbidden keywords appearing in SELECT clause."""
        # Extract SELECT clause
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_text, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1).lower()

            # Check each forbidden keyword
            for keyword in self.forbidden_keywords:
                if re.search(r"\b" + keyword + r"\b", select_clause):
                    result.errors.append(
                        f"Forbidden keyword '{keyword.upper()}' detected in SELECT clause. "
                        f"Only data retrieval operations are allowed in custom calculations."
                    )

    def _validate_select_statement(
        self, statement: sql.Statement, result: SQLValidationResult
    ) -> None:
        """Validate that this is a proper SELECT statement."""
        if statement.get_type() != "SELECT":
            result.errors.append("Only SELECT statements are allowed for custom SQL calculations")

    def _extract_table_aliases(self, statement: sql.Statement, result: SQLValidationResult) -> None:
        """Extract table aliases from FROM and JOIN clauses."""
        sql_text = str(statement).upper()

        # Common table alias patterns
        alias_patterns = [
            r"\bFROM\s+(\w+)\s+(?:AS\s+)?(\w+)(?:\s|,|$)",  # FROM table alias
            r"\bJOIN\s+(\w+)\s+(?:AS\s+)?(\w+)(?:\s|$)",  # JOIN table alias
        ]

        for pattern in alias_patterns:
            matches = re.finditer(pattern, sql_text)
            for match in matches:
                table_name = match.group(1).lower()
                alias = match.group(2).lower()
                if alias != table_name:  # Only store if it's actually an alias
                    result.table_aliases[alias] = table_name

    def _extract_select_columns(
        self, statement: sql.Statement, result: SQLValidationResult
    ) -> None:
        """Extract columns from the SELECT clause with improved parsing."""
        select_columns = []

        # Convert to string and use regex to find SELECT clause
        sql_text = str(statement)

        # Find the SELECT clause (everything between SELECT and FROM)
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_text, re.IGNORECASE | re.DOTALL)
        if not select_match:
            result.errors.append("Could not find SELECT clause in SQL")
            return

        select_clause = select_match.group(1).strip()

        # Parse the SELECT clause more robustly
        columns = self._parse_select_clause(select_clause)

        result.extracted_columns = columns

        if len(columns) == 0:
            result.errors.append("No columns found in SELECT statement")

    def _parse_select_clause(self, select_clause: str) -> List[str]:
        """Parse SELECT clause handling CASE statements, functions, and nested expressions."""
        columns = []
        current_column = ""
        paren_depth = 0
        case_depth = 0
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(select_clause):
            char = select_clause[i]

            # Handle quoted strings
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current_column += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_column += char
            elif in_quotes:
                current_column += char
            # Handle parentheses
            elif char == "(":
                paren_depth += 1
                current_column += char
            elif char == ")":
                paren_depth -= 1
                current_column += char
            # Handle CASE statements
            elif not in_quotes and select_clause[i : i + 4].upper() == "CASE":
                case_depth += 1
                current_column += select_clause[i : i + 4]
                i += 3  # Skip ahead
            elif not in_quotes and select_clause[i : i + 3].upper() == "END":
                case_depth -= 1
                current_column += select_clause[i : i + 3]
                i += 2  # Skip ahead
            # Handle column separators
            elif char == "," and paren_depth == 0 and case_depth == 0 and not in_quotes:
                if current_column.strip():
                    columns.append(current_column.strip())
                current_column = ""
            else:
                current_column += char

            i += 1

        # Add the last column
        if current_column.strip():
            columns.append(current_column.strip())

        return columns

    def _validate_required_fields_in_select(
        self, statement: sql.Statement, group_level: str, result: SQLValidationResult
    ) -> None:
        """Validate that required fields for the group level are present in the SELECT clause."""
        if group_level == "deal":
            required_fields = self.requirements.deal_level
        elif group_level == "tranche":
            required_fields = self.requirements.tranche_level
        else:
            result.errors.append(f"Invalid group level: {group_level}")
            return

        # Check each required field
        for required_field in required_fields:
            field_found = False

            # Check each SELECT column
            for column in result.extracted_columns:
                if required_field.matches_column(column, result.table_aliases):
                    field_found = True
                    break

            if not field_found:
                # Provide specific error message
                field_name = f"{required_field.table}.{required_field.column}"
                result.errors.append(
                    f"Required field '{field_name}' not found in SELECT clause for {group_level}-level calculation. "
                    f"This field must be explicitly selected to ensure proper grouping."
                )

    def _validate_result_column(
        self, expected_result_column: str, result: SQLValidationResult
    ) -> None:
        """Validate that the expected result column is present in SELECT."""
        found_result_column = False

        for column in result.extracted_columns:
            # Check for explicit alias
            if " AS " in column.upper():
                alias = column.split(" AS ")[-1].strip().strip("\"'")
                if alias.lower() == expected_result_column.lower():
                    found_result_column = True
                    result.result_column_name = alias
                    break
            # Check if the column expression ends with the expected name
            elif column.lower().strip().endswith(expected_result_column.lower()):
                found_result_column = True
                result.result_column_name = expected_result_column
                break

        if not found_result_column:
            result.warnings.append(
                f"Expected result column '{expected_result_column}' not found explicitly in SELECT clause. "
                f"Consider using 'AS {expected_result_column}' to make the result column clear."
            )
            result.result_column_name = expected_result_column

    def _extract_table_references(
        self, statement: sql.Statement, result: SQLValidationResult
    ) -> None:
        """Extract table references from the SQL."""
        tables = set()
        sql_text = str(statement).lower()

        # Look for table references in FROM and JOIN clauses
        table_patterns = [
            r"\bfrom\s+(\w+)",
            r"\bjoin\s+(\w+)",
            r"\binner\s+join\s+(\w+)",
            r"\bleft\s+join\s+(\w+)",
            r"\bright\s+join\s+(\w+)",
        ]

        for pattern in table_patterns:
            matches = re.finditer(pattern, sql_text)
            for match in matches:
                table_name = match.group(1)
                if table_name in ["deal", "tranche", "tranchebal"]:
                    tables.add(table_name)

        result.detected_tables = tables

        # Validate table usage for group level
        if not tables:
            result.warnings.append("No recognized tables found in SQL")

    def _validate_sql_structure(
        self, statement: sql.Statement, result: SQLValidationResult
    ) -> None:
        """Additional structural validation."""
        sql_text = str(statement).upper()

        # Check for required FROM clause
        if "FROM" not in sql_text:
            result.errors.append("SQL must include a FROM clause")

        # Warn about potentially expensive operations
        if "SELECT *" in sql_text:
            result.warnings.append(
                "SELECT * detected - consider specifying explicit columns for better performance"
            )

        if "ORDER BY" in sql_text:
            result.warnings.append("ORDER BY detected - this may impact performance in reports")

        # Check for proper JOIN syntax when multiple tables are involved
        if len(result.detected_tables) > 1:
            if "JOIN" not in sql_text:
                result.warnings.append(
                    "Multiple tables detected but no explicit JOIN found - ensure proper table relationships"
                )

        # Validate that we have the minimum required structure
        if len(result.extracted_columns) < 2:
            result.errors.append(
                "SQL must select at least the required grouping fields plus one result column"
            )


# Pydantic schema for validation
class CustomSQLCalculationCreate(BaseModel):
    """Schema for creating custom SQL calculations."""

    name: str
    description: Optional[str] = None
    group_level: str
    raw_sql: str
    result_column_name: str

    @validator("group_level")
    def validate_group_level(cls, v):
        if v not in ["deal", "tranche"]:
            raise ValueError("group_level must be 'deal' or 'tranche'")
        return v

    @validator("raw_sql")
    def validate_sql_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("raw_sql cannot be empty")
        return v.strip()

    @validator("result_column_name")
    def validate_result_column_name(cls, v):
        if not v or not v.strip():
            raise ValueError("result_column_name cannot be empty")
        # Validate column name format
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v.strip()):
            raise ValueError(
                "result_column_name must be a valid identifier (letters, numbers, underscores)"
            )
        return v.strip()


class SystemFieldCalculationCreate(BaseModel):
    """Schema for creating system field calculations."""

    name: str
    description: Optional[str] = None
    group_level: str
    source_model: str
    field_name: str
    field_type: str

    @validator("group_level")
    def validate_group_level(cls, v):
        if v not in ["deal", "tranche"]:
            raise ValueError("group_level must be 'deal' or 'tranche'")
        return v

    @validator("source_model")
    def validate_source_model(cls, v):
        if v not in ["Deal", "Tranche", "TrancheBal"]:
            raise ValueError("source_model must be one of: Deal, Tranche, TrancheBal")
        return v


# Example usage function
def validate_example_sql():
    """Example validation function."""
    validator = CustomSQLValidator()

    # Example valid SQL for deal-level calculation
    sql = """
    SELECT 
        deal.dl_nbr,
        CASE 
            WHEN deal.issr_cde = 'FHLMC' THEN 'Government Sponsored'
            WHEN deal.issr_cde = 'GNMA' THEN 'Government'
            ELSE 'Private'
        END AS issuer_type
    FROM deal
    WHERE deal.dl_nbr IN (1001, 1002, 1003)
    """

    result = validator.validate_custom_sql(sql, "deal", "issuer_type")
    return result
