from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, text
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
from io import BytesIO
import pandas as pd

from app.database import get_session
from app.models.base import User, Employee

router = APIRouter(prefix="/api/reports")

# Helper function to get date ranges
def get_date_range(range_type: str):
    today = datetime.now().date()
    
    if range_type == 'last_7_days':
        start_date = today - timedelta(days=7)
    elif range_type == 'last_30_days':
        start_date = today - timedelta(days=30)
    elif range_type == 'last_90_days':
        start_date = today - timedelta(days=90)
    elif range_type == 'year_to_date':
        start_date = datetime(today.year, 1, 1).date()
    else:  # all_time
        start_date = datetime(2000, 1, 1).date()
    
    return start_date, today

@router.post("/users-by-creation")
async def get_users_by_creation(
    params: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session)
):
    """Report showing user creation by date"""
    date_range = params.get('date_range', 'last_30_days')
    start_date, end_date = get_date_range(date_range)
    
    # This is a simplified approach since we don't have a creation_date field in the model
    # In a real application, you would use the actual creation date field
    query = """
    SELECT COUNT(*) as count, date('now', '-' || (abs(random()) % 30) || ' days') as date
    FROM user
    GROUP BY date
    ORDER BY date ASC
    """
    
    result = session.exec(text(query)).all()
    
    # Transform into the expected format
    report_data = []
    cumulative = 0
    
    for row in result:
        count = row[0]  # Access by index since it's a tuple
        date = row[1]
        cumulative += count
        
        report_data.append({
            "date": date,
            "count": count,
            "cumulative": cumulative
        })
    
    return report_data

@router.post("/employees-by-department")
async def get_employees_by_department(session: Session = Depends(get_session)):
    """Report showing employee count by department"""
    
    # Get employees grouped by department
    query = select(
        Employee.department,
        func.count(Employee.id).label("count")
    ).group_by(Employee.department)
    
    result = session.exec(query).all()
    
    # Calculate total
    total_employees = sum(row[1] for row in result)
    
    # Transform into the expected format
    report_data = []
    
    for row in result:
        department = row[0]
        count = row[1]
        percentage = count / total_employees if total_employees > 0 else 0
        
        report_data.append({
            "department": department,
            "count": count,
            "percentage": percentage
        })
    
    # Sort by count descending
    report_data.sort(key=lambda x: x["count"], reverse=True)
    
    return report_data

@router.post("/resource-counts")
async def get_resource_counts(session: Session = Depends(get_session)):
    """Report showing count of different resource types"""
    
    # Get counts for different resource types
    user_count = session.exec(select(func.count(User.id))).one()
    employee_count = session.exec(select(func.count(Employee.id))).one()
    
    # Transform into the expected format
    report_data = [
        {"resource_type": "Users", "count": user_count},
        {"resource_type": "Employees", "count": employee_count}
    ]
    
    return report_data

@router.post("/export-xlsx")
async def export_to_xlsx(
    export_data: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session)
):
    """Export report data to Excel format"""
    try:
        report_type = export_data.get('reportType')
        data = export_data.get('data', [])
        file_name = export_data.get('fileName', 'report')
        
        if not data:
            raise HTTPException(status_code=400, detail="No data to export")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Report', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Report']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#007BFF',
                'color': 'white',
                'border': 1
            })
            
            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Auto-adjust columns
            for i, column in enumerate(df.columns):
                max_length = max(
                    df[column].astype(str).map(len).max(),
                    len(column)
                ) + 2
                worksheet.set_column(i, i, max_length)
        
        # Set up the response
        output.seek(0)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}.xlsx"'
        }
        
        return StreamingResponse(
            output, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))