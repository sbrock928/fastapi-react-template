from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from app.database import get_session
from app.models.base import User, UserBase
from app.service.user_service import UserService

router = APIRouter()

@router.get("/users", response_model=List[User])
async def list_users(session: Session = Depends(get_session)):
    user_service = UserService(session)
    return await user_service.get_all_users()

@router.post("/users", response_model=User)
async def create_user(user_data: UserBase, session: Session = Depends(get_session)):
    user_service = UserService(session)
    return await user_service.create_user(user_data)

@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int, session: Session = Depends(get_session)):
    user_service = UserService(session)
    return await user_service.get_user_by_id(user_id)

@router.patch("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserBase,
    session: Session = Depends(get_session)
):
    user_service = UserService(session)
    return await user_service.update_user(user_id, user_update)

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    user_service = UserService(session)
    return await user_service.delete_user(user_id)