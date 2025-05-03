from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class LogBase(SQLModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    method: str
    path: str
    status_code: int
    client_ip: Optional[str] = None
    request_headers: Optional[str] = None
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    processing_time: Optional[float] = None  # in milliseconds
    user_agent: Optional[str] = None
    
    class Config:
        orm_mode = True
        extra = "forbid"

# Database table model (inherits from base model)
class Log(LogBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)