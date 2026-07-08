"""SQLAlchemy implementation for user authentication."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User, LoginRecord, Profile


class SqlAlchemyUserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, username: str, password_hash: str, preferred_language: str = "zh-CN") -> str:
        user_id = f"orm-{uuid.uuid4().hex[:16]}"
        user = User(
            id=user_id,
            username=username,
            password_hash=password_hash,
            preferred_language=preferred_language,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(user)
        self.session.flush()
        return user_id

    def get_by_username(self, username: str) -> User | None:
        return self.session.query(User).filter_by(username=username).first()

    def record_login(self, user_id: str, ip: str = "", user_agent: str = "") -> None:
        record = LoginRecord(
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
            login_at=datetime.now(timezone.utc),
        )
        self.session.add(record)
        self.session.flush()

    def get_login_history(self, user_id: str) -> list:
        records = self.session.query(LoginRecord).filter_by(user_id=user_id).order_by(LoginRecord.login_at.desc()).all()
        return [
            {"id": r.id, "ip": r.ip_address, "user_agent": r.user_agent, "login_at": r.login_at.isoformat()}
            for r in records
        ]
