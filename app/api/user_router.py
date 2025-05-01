from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.base import User
from sqlalchemy.exc import IntegrityError

router = APIRouter()

async def check_user_exists(username: str, email: str, session: Session, exclude_id: int = None) -> None:
    # Check username
    username_query = select(User).where(User.username == username)
    if exclude_id:
        username_query = username_query.where(User.id != exclude_id)
    existing_username = session.exec(username_query).first()
    if existing_username:
        raise HTTPException(status_code=400, detail={"username": "Username already exists"})
    
    # Check email
    email_query = select(User).where(User.email == email)
    if exclude_id:
        email_query = email_query.where(User.id != exclude_id)
    existing_email = session.exec(email_query).first()
    if existing_email:
        raise HTTPException(status_code=400, detail={"email": "Email already exists"})

@router.get("/", response_model=List[User])
async def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return users

@router.post("/", response_model=User)
async def create_user(user: User, session: Session = Depends(get_session)):
    await check_user_exists(user.username, user.email, session)
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=400, detail="Database constraint violated")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user: User,
    session: Session = Depends(get_session)
):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get only the fields that were actually provided in the request
    # Try with dict() instead of model_dump() for compatibility
    try:
        update_data = user.dict(exclude_unset=True)
    except AttributeError:
        # For newer versions of SQLModel/Pydantic
        update_data = user.model_dump(exclude_unset=True)
    
    # Remove id from update data to prevent changing it
    if "id" in update_data:
        del update_data["id"]
    
    # Check uniqueness for username and email if they are being updated
    if update_data.get('username') or update_data.get('email'):
        await check_user_exists(
            username=update_data.get('username', db_user.username),
            email=update_data.get('email', db_user.email),
            session=session,
            exclude_id=user_id
        )
    
    # Update the user object with the provided fields
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception as e:
        session.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=400, detail="Database constraint violated")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    session.delete(user)
    session.commit()
    return {"status": "success"}