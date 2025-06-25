# app/utils/__init__.py
"""Utility functions package"""

def convert_cycle_code_to_date(cycle_code: int) -> str:
    """
    Convert a cycle code integer to a date string in MM/DD/YYYY format.
    
    Based on the pattern: 12503 → 3/1/2025 (always first of the month)
    
    The cycle code is encoded as: YYMM + fixed suffix where:
    - YY: Last two digits of year (25 = 2025) 
    - MM: Month (03 = March, 04 = April, etc.)
    - Always represents the 1st day of the month
    
    Examples:
    - 12503 = 3/1/2025 (March 1st, 2025)
    - 12504 = 4/1/2025 (April 1st, 2025) 
    - 12512 = 12/1/2025 (December 1st, 2025)
    
    Args:
        cycle_code: Integer cycle code (e.g., 12503)
        
    Returns:
        Date string in M/D/YYYY format (e.g., "3/1/2025")
    """
    try:
        # Convert to string to parse digits
        code_str = str(cycle_code)
        
        # Handle different cycle code lengths
        if len(code_str) == 5:  # e.g., 12503
            # Parse as YYMM + suffix
            year_part = code_str[:2]    # "12" -> but this should be "25" for 2025
            # Actually, let's re-examine: 12503 = 3/1/2025
            # So "125" might be year 2025, and "03" is month
            # Let's try: first 3 digits for year, last 2 for month
            year_part = code_str[:3]    # "125" 
            month_part = code_str[3:]   # "03"
            
            # Extract year from the 3-digit year part
            # 125 -> 2025 (need to figure out the encoding)
            # Let's try a different approach: 12503 for March 2025
            # Maybe it's: 1(decade) + 25(year digits) + 03(month)
            # Or: 125(encoded year) + 03(month)
            
            # Let's go with a simpler interpretation based on your examples:
            # 12503 = March 1, 2025 -> maybe "25" is year, "03" is month
            # So positions might be: X + YY + MM where X is some prefix
            
            # Try: position 1-2 for year, position 3-4 for month
            if len(code_str) == 5:
                year_part = code_str[1:3]   # Position 1-2: "25" from "12503"
                month_part = code_str[3:5]  # Position 3-4: "03" from "12503"
            else:
                return str(cycle_code)  # Fallback
                
        elif len(code_str) == 4:  # e.g., 2503 for shorter format
            # Parse as YYMM
            year_part = code_str[:2]    # "25"
            month_part = code_str[2:]   # "03"
            
        else:
            # Fallback - return the original code as string
            return str(cycle_code)
        
        # Convert year to full year (YY -> YYYY)
        try:
            year_int = int(year_part)
            if year_int >= 0 and year_int <= 30:  # Assume 2000-2030
                full_year = 2000 + year_int
            else:  # Assume 1900s for higher numbers  
                full_year = 1900 + year_int
        except ValueError:
            return str(cycle_code)
            
        # Convert month
        try:
            month_int = int(month_part)
            # Validate month range
            if month_int < 1 or month_int > 12:
                return str(cycle_code)  # Invalid month
        except ValueError:
            return str(cycle_code)
            
        # Always use day = 1 (first of the month)
        day_int = 1
            
        # Format as M/D/YYYY (no leading zeros for month/day)
        return f"{month_int}/{day_int}/{full_year}"
        
    except (ValueError, IndexError):
        # If parsing fails, return the original code
        return str(cycle_code)


def format_cycle_code_for_display(cycle_code: int, format_type: str = "code") -> str:
    """
    Format a cycle code for display based on the selected format type.
    
    Args:
        cycle_code: The cycle code integer
        format_type: Format type - "code" shows the number, "date" shows MM/DD/YYYY format
        
    Returns:
        Formatted string for display
    """
    if format_type.lower() in ["date", "date mm/dd/yyyy", "mm/dd/yyyy"]:
        return convert_cycle_code_to_date(cycle_code)
    else:
        return str(cycle_code)


def test_cycle_code_conversion():
    """Test function to validate cycle code conversion logic"""
    test_cases = [
        (12503, "3/1/2025"),   # March 1st, 2025
        (12504, "4/1/2025"),   # April 1st, 2025  
        (12505, "5/1/2025"),   # May 1st, 2025
        (12512, "12/1/2025"),  # December 1st, 2025
        (12401, "1/1/2024"),   # January 1st, 2024
        (12412, "12/1/2024"),  # December 1st, 2024
    ]
    
    results = []
    for cycle_code, expected in test_cases:
        result = convert_cycle_code_to_date(cycle_code)
        results.append({
            "cycle_code": cycle_code,
            "expected": expected,
            "actual": result,
            "matches": result == expected
        })
    
    return results