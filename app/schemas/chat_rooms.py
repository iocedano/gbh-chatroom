from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Room name cannot be blank")
        return value


class ChatRoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()
        if not value:
            raise ValueError("Room name cannot be blank")
        return value


class ChatRoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_by: int
    created_at: datetime
