from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import Base

if TYPE_CHECKING:
    from .message import Message
    from .room_member import RoomMember
    from .user import User


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    creator: Mapped["User"] = relationship(back_populates="rooms_created")
    messages: Mapped[list["Message"]] = relationship(back_populates="room")
    members: Mapped[list["RoomMember"]] = relationship(back_populates="room", cascade="all, delete-orphan")
