from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class LogBase(BaseModel):
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
    username: Optional[str] = None
    hostname: Optional[str] = None
    application_id: Optional[str] = Field(default=None, title="Application ID")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class LogCreate(LogBase):
    pass


class LogRead(LogBase):
    id: int
