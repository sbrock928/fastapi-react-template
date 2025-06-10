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

class GroupLevelRequirements(BaseModel):
    """Requirements for different group levels."""
    deal_level: List[RequiredField] = [
        RequiredField(table="deal", column="dl_nbr")
    ]
    tranche_level: List[RequiredField] = [
        RequiredField(table="deal", column="dl_nbr"),
        RequiredField(table="tranche", column="tr_id")
    ]

class SQLValidationResult(BaseModel):
    """Result of SQL validation."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    extracted_columns: List[str] = []
    detected_tables: Set[str] = set()
    result_column_name: Optional[str] = None

class CustomSQLValidator:
    """Validates custom SQL for system calculations."""
    
    def __init__(self):
        self.requirements = GroupLevelRequirements()
        # Common SQL injection patterns to block
        self.dangerous_patterns = [
            r'(?i)\bdrop\s+table\b',
            r'(?i)\bdelete\s+from\b',
            r'(?i)\binsert\s+into\b',
            r'(?i)\bupdate\s+.*\bset\b',
            r'(?i)\balter\s+table\b',
            r'(?i)\bcreate\s+table\b',
            r'(?i)\btruncate\s+table\b',
            r'(?i)\bexec\s*\(',
            r'(?i)\bexecute\s*\(',
            r'(?i)--',  # SQL comments
            r'(?i)/\*.*\*/',  # Block comments
        ]
        
    def validate_custom_sql(self, sql_text: str, group_level: str, expected_result_column: str) -> SQLValidationResult:
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
            
            # 4. Extract and validate columns
            self._extract_and_validate_columns(statement, expected_result_column, result)
            
            # 5. Validate required fields for group level
            self._validate_group_level_requirements(statement, group_level, result)
            
            # 6. Extract table references
            self._extract_table_references(statement, result)
            
            # 7. Additional structural validation
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
                result.errors.append(f"Dangerous SQL pattern detected: {pattern}")
        
        # Check for multiple statements (should be single SELECT)
        statements = sqlparse.split(sql_text)
        if len(statements) > 1:
            result.errors.append("Multiple SQL statements not allowed - only single SELECT statements permitted")
    
    def _validate_select_statement(self, statement: sql.Statement, result: SQLValidationResult) -> None:
        """Validate that this is a proper SELECT statement."""
        if statement.get_type() != 'SELECT':
            result.errors.append("Only SELECT statements are allowed for custom SQL calculations")
    
    def _extract_and_validate_columns(self, statement: sql.Statement, expected_result_column: str, result: SQLValidationResult) -> None:
        """Extract and validate the SELECT columns."""
        select_columns = []
        
        # Use sqlparse to properly extract the SELECT list
        select_found = False
        for token in statement.tokens:
            if token.ttype is tokens.Keyword and token.value.upper() == 'SELECT':
                select_found = True
                continue
            elif select_found and isinstance(token, sql.IdentifierList):
                # Multiple columns
                for identifier in token.get_identifiers():
                    select_columns.append(str(identifier).strip())
                break
            elif select_found and token.ttype not in (tokens.Whitespace, tokens.Newline):
                if token.ttype is tokens.Keyword and token.value.upper() in ('FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING'):
                    break
                elif str(token).strip() and str(token).strip() != ',':
                    select_columns.append(str(token).strip())
                    break
        
        # If we didn't find columns using the above method, try a different approach
        if not select_columns:
            sql_text = str(statement)
            # Extract everything between SELECT and FROM
            match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_text, re.IGNORECASE | re.DOTALL)
            if match:
                columns_text = match.group(1).strip()
                # Split by comma but be careful with CASE statements
                select_columns = self._parse_select_list(columns_text)
        
        result.extracted_columns = select_columns
        
        # Validate column count and structure
        if len(select_columns) == 0:
            result.errors.append("No columns found in SELECT statement")
            return
        
        # For system SQL calculations, we need to be more flexible
        # Look for the result column (the one with the expected alias)
        found_result_column = False
        for col in select_columns:
            if ' AS ' in col.upper():
                alias = col.split(' AS ')[-1].strip().strip('"\'')
                if alias.lower() == expected_result_column.lower():
                    found_result_column = True
                    result.result_column_name = alias
                    break
        
        if not found_result_column:
            # Check if the expected column name appears in any column
            for col in select_columns:
                if expected_result_column.lower() in col.lower():
                    found_result_column = True
                    result.result_column_name = expected_result_column
                    break
        
        if not found_result_column:
            result.warnings.append(f"Expected result column '{expected_result_column}' not found explicitly")
            result.result_column_name = expected_result_column
    
    def _parse_select_list(self, columns_text: str) -> List[str]:
        """Parse the SELECT column list, handling CASE statements properly."""
        columns = []
        current_col = ""
        paren_depth = 0
        case_depth = 0
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(columns_text):
            char = columns_text[i]
            
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current_col += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_col += char
            elif in_quotes:
                current_col += char
            elif char == '(':
                paren_depth += 1
                current_col += char
            elif char == ')':
                paren_depth -= 1
                current_col += char
            elif char.upper() == 'C' and columns_text[i:i+4].upper() == 'CASE':
                case_depth += 1
                current_col += char
            elif char.upper() == 'E' and columns_text[i:i+3].upper() == 'END':
                case_depth -= 1
                current_col += char
            elif char == ',' and paren_depth == 0 and case_depth == 0:
                if current_col.strip():
                    columns.append(current_col.strip())
                current_col = ""
            else:
                current_col += char
            
            i += 1
        
        # Add the last column
        if current_col.strip():
            columns.append(current_col.strip())
        
        return columns
    
    def _get_required_fields_for_group_level(self, statement: sql.Statement) -> List[RequiredField]:
        """Get required fields based on detected group level."""
        # For now, return tranche level requirements (most restrictive)
        # In a more sophisticated implementation, we could detect the group level from the SQL
        return self.requirements.tranche_level
    
    def _validate_group_level_requirements(self, statement: sql.Statement, group_level: str, result: SQLValidationResult) -> None:
        """Validate that required fields for the group level are present."""
        sql_text = str(statement).lower()
        
        if group_level == 'deal':
            required_fields = self.requirements.deal_level
        elif group_level == 'tranche':
            required_fields = self.requirements.tranche_level
        else:
            result.errors.append(f"Invalid group level: {group_level}")
            return
        
        for field in required_fields:
            field_pattern = f"{field.table}.{field.column}"
            if field_pattern not in sql_text:
                result.errors.append(f"Required field '{field_pattern}' not found in SQL for {group_level}-level calculation")
    
    def _extract_table_references(self, statement: sql.Statement, result: SQLValidationResult) -> None:
        """Extract table references from the SQL."""
        tables = set()
        sql_text = str(statement).lower()
        
        # Look for common table references
        if 'deal' in sql_text:
            tables.add('deal')
        if 'tranche' in sql_text:
            tables.add('tranche')
        if 'tranchebal' in sql_text:
            tables.add('tranchebal')
        
        result.detected_tables = tables
    
    def _normalize_column_reference(self, column: str) -> str:
        """Normalize column reference for comparison."""
        # Remove extra whitespace, quotes, etc.
        return column.strip().strip('"\'').lower()
    
    def _validate_sql_structure(self, statement: sql.Statement, result: SQLValidationResult) -> None:
        """Additional structural validation."""
        sql_text = str(statement).upper()
        
        # Check for required FROM clause
        if 'FROM' not in sql_text:
            result.errors.append("SQL must include a FROM clause")
        
        # Warn about potentially expensive operations
        if 'SELECT *' in sql_text:
            result.warnings.append("SELECT * detected - consider specifying explicit columns for better performance")
        
        if 'ORDER BY' in sql_text:
            result.warnings.append("ORDER BY detected - this may impact performance in reports")

# Pydantic schema for validation
class CustomSQLCalculationCreate(BaseModel):
    """Schema for creating custom SQL calculations."""
    name: str
    description: Optional[str] = None
    group_level: str
    raw_sql: str
    result_column_name: str
    
    @validator('group_level')
    def validate_group_level(cls, v):
        if v not in ['deal', 'tranche']:
            raise ValueError("group_level must be 'deal' or 'tranche'")
        return v
    
    @validator('raw_sql')
    def validate_sql_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("raw_sql cannot be empty")
        return v.strip()
    
    @validator('result_column_name')
    def validate_result_column_name(cls, v):
        if not v or not v.strip():
            raise ValueError("result_column_name cannot be empty")
        # Validate column name format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v.strip()):
            raise ValueError("result_column_name must be a valid identifier (letters, numbers, underscores)")
        return v.strip()

class SystemFieldCalculationCreate(BaseModel):
    """Schema for creating system field calculations."""
    name: str
    description: Optional[str] = None
    group_level: str
    source_model: str
    field_name: str
    field_type: str
    
    @validator('group_level')
    def validate_group_level(cls, v):
        if v not in ['deal', 'tranche']:
            raise ValueError("group_level must be 'deal' or 'tranche'")
        return v
    
    @validator('source_model')
    def validate_source_model(cls, v):
        if v not in ['Deal', 'Tranche', 'TrancheBal']:
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
    
    result = validator.validate_custom_sql(sql, 'deal', 'issuer_type')
    return result