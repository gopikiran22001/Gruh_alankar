"""Gruha Alankara — User Model (Pydantic)."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=100)


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str = ""
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class UserInDB(BaseModel):
    username: str
    email: str
    password_hash: str
    full_name: str = ""
    preferences: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
