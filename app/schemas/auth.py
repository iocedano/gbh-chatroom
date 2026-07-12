from pydantic import BaseModel

from .users import UserRead


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(Token):
    user: UserRead
