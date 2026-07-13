import itertools
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_current_user
from infra.database import get_db
from main import app
from models.base_model import Base
from schemas.chat_rooms import ChatRoomCreate
from schemas.messages import MessageCreate
from schemas.users import UserCreate
from services.auth import create_access_token
from services.chat_rooms import create_chat_room, join_chat_room
from services.messages import create_message
from services.users import register_user


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fixture_factory(db_session: Session):
    counter = itertools.count(1)

    class FixtureFactory:
        def user(self, username: str | None = None, password: str = "password123"):
            suffix = next(counter)
            return register_user(
                db_session,
                UserCreate(username=username or f"user{suffix}", password=password),
            )

        def token(self, user) -> str:
            return create_access_token(subject=str(user.id))

        def auth_headers(self, user) -> dict[str, str]:
            return {"Authorization": f"Bearer {self.token(user)}"}

        def room(self, creator, name: str | None = None):
            suffix = next(counter)
            return create_chat_room(
                db_session,
                ChatRoomCreate(name=name or f"Room {suffix}"),
                created_by=creator.id,
            )

        def join(self, room, user):
            return join_chat_room(db_session, room.id, user_id=user.id)

        def message(self, room, sender, content: str = "Hello", idempotency_key: str | None = None):
            suffix = next(counter)
            return create_message(
                db_session,
                room.id,
                MessageCreate(content=content),
                sender_id=sender.id,
                idempotency_key=idempotency_key or f"fixture-{suffix}",
            )

    return FixtureFactory()


@pytest.fixture(autouse=True)
def clear_current_user_override():
    yield
    app.dependency_overrides.pop(get_current_user, None)
