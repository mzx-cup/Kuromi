"""Audit 命名空间.

P0 阶段: 仅暴露 `registration_guard` 角色白名单.
P1 阶段: 补充 admin 操作审计 (e.g. role 提升, 教师创建班级) 等.
"""
from app.services.audit.registration_guard import (  # noqa: F401
    ALLOWED_SELF_REGISTER_ROLES,
    assert_self_register_role_allowed,
)

__all__ = [
    "ALLOWED_SELF_REGISTER_ROLES",
    "assert_self_register_role_allowed",
]
