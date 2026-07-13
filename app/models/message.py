from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import Base

if TYPE_CHECKING:
    from .chat_room import ChatRoom
    from .user import User


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("room_id", "sender_id", "idempotency_key", name="uq_messages_room_sender_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    room: Mapped["ChatRoom"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship(back_populates="messages")

    @property
    def sender_username(self) -> str:
        return self.sender.username
