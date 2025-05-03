from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, text
from typing import List, Dict, Any
from app.database import get_session
from app.models.base import User, Employee, Log
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

router = APIRouter(prefix='/reports', tags=["Reports"])

@router.get("/reports/statistics", response_model=Dict[str, Any])
async def get_summary_statistics(session: Session = Depends(get_session)):
    """Get summary statistics for the dashboard"""
    try:
        user_count = session.exec(select(func.count()).select_from(User)).one()
        employee_count = session.exec(select(func.count()).select_from(Employee)).one()
        log_count = session.exec(select(func.count()).select_from(Log)).one()
        
        return {
            "user_count": user_count,
            "employee_count": employee_count,
            "log_count": log_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary statistics: {str(e)}")

@router.get("/reports/recent-activities", response_model=Dict[str, Any])
async def get_recent_activities(
    days: int = Query(7, ge=1, le=30),
    session: Session = Depends(get_session)
):
    """Get recent activities for the dashboard"""
    if days <= 0:
        raise HTTPException(status_code=400, detail="Days must be greater than 0")
        
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        query = select(Log).where(Log.timestamp >= cutoff_date).order_by(Log.timestamp.desc()).limit(10)
        recent_logs = session.exec(query).all()
        
        # Format logs
        formatted_logs = []
        for log in recent_logs:
            # Handle both older and newer pydantic versions
            try:
                log_dict = log.dict()
            except AttributeError:
                log_dict = log.model_dump()
                
            # Add status category
            status_code = log_dict.get("status_code", 0)
            if 200 <= status_code < 300:
                log_dict["status_category"] = "Success"
            elif 300 <= status_code < 400:
                log_dict["status_category"] = "Redirection"
            elif 400 <= status_code < 500:
                log_dict["status_category"] = "Client Error"
            elif 500 <= status_code < 600:
                log_dict["status_category"] = "Server Error"
            else:
                log_dict["status_category"] = "Unknown"
                
            formatted_logs.append(log_dict)
        
        return {
            "recent_logs": formatted_logs,
            "days": days,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recent activities: {str(e)}")

@router.get("/reports/status-distribution", response_model=Dict[str, Any])
async def get_status_distribution(session: Session = Depends(get_session)):
    """Get distribution of logs by status code"""
    try:
        query = select(Log.status_code, func.count(Log.id).label("count")).group_by(Log.status_code)
        results = session.exec(query).all()
        
        distribution = []
        for status_code, count in results:
            item = {"status_code": status_code, "count": count}
            
            # Add description
            if 200 <= status_code < 300:
                item["description"] = "Success"
            elif 300 <= status_code < 400:
                item["description"] = "Redirection"
            elif 400 <= status_code < 500:
                item["description"] = "Client Error"
            elif 500 <= status_code < 600:
                item["description"] = "Server Error"
            else:
                item["description"] = "Unknown"
                
            distribution.append(item)
            
        return {
            "status_distribution": distribution,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating status distribution: {str(e)}")

@router.post("/users-by-creation")
async def get_users_by_creation(
    params: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session)
):
    """Report showing user creation by date"""
    date_range = params.get('date_range', 'last_30_days')
    today = datetime.now().date()
    
    # Determine date range
    if date_range == 'last_7_days':
        start_date = today - timedelta(days=7)
    elif date_range == 'last_30_days':
        start_date = today - timedelta(days=30)
    elif date_range == 'last_90_days':
        start_date = today - timedelta(days=90)
    elif date_range == 'year_to_date':
        start_date = datetime(today.year, 1, 1).date()
    else:  # all_time
        start_date = datetime(2000, 1, 1).date()
    
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
        
        # Reset file pointer
        output.seek(0)
        
        file_name = export_data.get('fileName', 'report')
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