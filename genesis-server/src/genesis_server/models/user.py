from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    full_name: str | None = None
    email: str | None = Field(index=True, unique=True)
    disabled: bool = Field(default=False)
    working_directory: str | None = None


class User(UserBase, table=True):
    """The actual Database Table"""

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
