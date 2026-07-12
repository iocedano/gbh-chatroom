from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.room_member import RoomMember


def create_room_member(db: Session, *, room_id: int, user_id: int) -> RoomMember:
    membership = RoomMember(room_id=room_id, user_id=user_id)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def get_active_room_member(db: Session, *, room_id: int, user_id: int) -> RoomMember | None:
    statement = select(RoomMember).where(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
        RoomMember.left_at.is_(None),
    )
    return db.scalar(statement)


def get_latest_room_member(db: Session, *, room_id: int, user_id: int) -> RoomMember | None:
    statement = (
        select(RoomMember)
        .where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
        .order_by(RoomMember.joined_at.desc(), RoomMember.id.desc())
    )
    return db.scalar(statement)


def list_active_room_members(db: Session, *, room_id: int) -> list[RoomMember]:
    statement = select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.left_at.is_(None))
    return list(db.scalars(statement))


def list_user_active_memberships(db: Session, *, user_id: int) -> list[RoomMember]:
    statement = select(RoomMember).where(RoomMember.user_id == user_id, RoomMember.left_at.is_(None))
    return list(db.scalars(statement))


def reactivate_room_member(db: Session, membership: RoomMember) -> RoomMember:
    membership.left_at = None
    membership.joined_at = datetime.now(timezone.utc)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def leave_room_member(db: Session, membership: RoomMember) -> RoomMember:
    membership.left_at = datetime.now(timezone.utc)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership
