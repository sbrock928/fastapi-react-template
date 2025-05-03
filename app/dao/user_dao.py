from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.models.base import User
from sqlalchemy.exc import IntegrityError

class UserDAO:
    def __init__(self, session: Session):
        self.session = session
    
    async def get_all_users(self) -> List[User]:
        """Get all users from the database"""
        users = self.session.exec(select(User)).all()
        return users
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        user = self.session.get(User, user_id)
        return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        user_query = select(User).where(User.username == username)
        user = self.session.exec(user_query).first()
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        user_query = select(User).where(User.email == email)
        user = self.session.exec(user_query).first()
        return user
    
    async def create_user(self, user: User) -> User:
        """Create a new user"""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    async def update_user(self, user: User) -> User:
        """Update an existing user"""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    async def delete_user(self, user: User) -> None:
        """Delete a user"""
        self.session.delete(user)
        self.session.commit()