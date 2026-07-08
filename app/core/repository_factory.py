"""Factory for instantiating repositories based on feature flags."""
from __future__ import annotations

from app.core.feature_flags import (
    get_read_percentage,
    is_dual_write_enabled,
    is_orm_enabled,
    user_in_orm_read_path,
)
from app.repositories.base import (
    LearningRepository,
    PreferencesRepository,
    ChatRepository,
)
from app.repositories.dual_write import DualWriteRepository


def is_orm_read_path_active(user_id: str) -> bool:
    if not is_orm_enabled():
        return False
    return user_in_orm_read_path(user_id, get_read_percentage())


def _build_orm(repository_type: str):
    if repository_type == "learning":
        from app.repositories.orm.learning import SqlAlchemyLearningRepository
        return SqlAlchemyLearningRepository
    if repository_type == "preferences":
        from app.repositories.orm.preferences import SqlAlchemyPreferencesRepository
        return SqlAlchemyPreferencesRepository
    raise ValueError(f"Unknown repository_type: {repository_type}")


def _build_legacy(repository_type: str):
    if repository_type == "learning":
        from app.repositories.legacy.learning import DbPyLearningRepository
        return DbPyLearningRepository
    if repository_type == "preferences":
        from app.repositories.legacy.preferences import DbPyPreferencesRepository
        return DbPyPreferencesRepository
    raise ValueError(f"Unknown repository_type: {repository_type}")


def get_repository_for_user(user_id: str, repository_type: str):
    """Get the read-path repository for this user.

    If ORM read path is active for this user, return ORM repository.
    Otherwise return legacy repository.
    """
    if is_orm_read_path_active(user_id):
        orm_cls = _build_orm(repository_type)
        return orm_cls()
    legacy_cls = _build_legacy(repository_type)
    return legacy_cls()


def get_write_repository(user_id: str, repository_type: str, db_session=None):
    """Get the write-path repository.

    If dual-write is enabled, wraps primary and shadow in DualWriteRepository.
    Otherwise returns just the primary.
    """
    primary_cls = _build_orm(repository_type)
    primary = primary_cls(db_session) if db_session else primary_cls()

    if is_dual_write_enabled():
        shadow_cls = _build_legacy(repository_type)
        shadow = shadow_cls()
        return DualWriteRepository(primary=primary, shadow=shadow)

    return primary
