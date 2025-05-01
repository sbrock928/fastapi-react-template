from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.base import Employee
from sqlalchemy.exc import IntegrityError

router = APIRouter()

async def check_employee_exists(employee_id: str, email: str, session: Session, exclude_id: int = None) -> None:
    # Check employee_id
    employee_id_query = select(Employee).where(Employee.employee_id == employee_id)
    if exclude_id:
        employee_id_query = employee_id_query.where(Employee.id != exclude_id)
    existing_employee_id = session.exec(employee_id_query).first()
    if existing_employee_id:
        raise HTTPException(status_code=400, detail={"employee_id": "Employee ID already exists"})
    
    # Check email
    email_query = select(Employee).where(Employee.email == email)
    if exclude_id:
        email_query = email_query.where(Employee.id != exclude_id)
    existing_email = session.exec(email_query).first()
    if existing_email:
        raise HTTPException(status_code=400, detail={"email": "Email already exists"})

@router.get("/", response_model=List[Employee])
async def list_employees(session: Session = Depends(get_session)):
    employees = session.exec(select(Employee)).all()
    return employees

@router.post("/", response_model=Employee)
async def create_employee(employee: Employee, session: Session = Depends(get_session)):
    await check_employee_exists(employee.employee_id, employee.email, session)
    session.add(employee)
    try:
        session.commit()
        session.refresh(employee)
        return employee
    except Exception as e:
        session.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=400, detail="Database constraint violated")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{employee_id}", response_model=Employee)
async def get_employee(employee_id: int, session: Session = Depends(get_session)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@router.patch("/{employee_id}", response_model=Employee)
async def update_employee(
    employee_id: int,
    employee: Employee,
    session: Session = Depends(get_session)
):
    db_employee = session.get(Employee, employee_id)
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get only the fields that were actually provided in the request
    # Try with dict() instead of model_dump() for compatibility
    try:
        update_data = employee.dict(exclude_unset=True)
    except AttributeError:
        # For newer versions of SQLModel/Pydantic
        update_data = employee.model_dump(exclude_unset=True)
    
    # Remove id from update data to prevent changing it
    if "id" in update_data:
        del update_data["id"]
    
    # Check uniqueness for employee_id and email if they are being updated
    if update_data.get('employee_id') or update_data.get('email'):
        await check_employee_exists(
            employee_id=update_data.get('employee_id', db_employee.employee_id),
            email=update_data.get('email', db_employee.email),
            session=session,
            exclude_id=employee_id
        )
    
    # Update the employee object with the provided fields
    for key, value in update_data.items():
        setattr(db_employee, key, value)
    
    try:
        session.add(db_employee)
        session.commit()
        session.refresh(db_employee)
        return db_employee
    except Exception as e:
        session.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=400, detail="Database constraint violated")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{employee_id}")
async def delete_employee(employee_id: int, session: Session = Depends(get_session)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    session.delete(employee)
    session.commit()
    return {"status": "success"}