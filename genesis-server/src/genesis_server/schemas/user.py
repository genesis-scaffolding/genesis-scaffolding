from pydantic import BaseModel

from ..models.user import UserBase


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    current_password: str | None = None  # Required to verify identity for sensitive changes
    new_password: str | None = None
