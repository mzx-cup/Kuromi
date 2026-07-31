# -*- coding: utf-8 -*-
"""注册角色白名单 (比赛版只允许 self-registered role = student).

设计动机:
- 防止攻击者通过 `/api/auth/register` 自助提升为 teacher/admin.
- 比赛版 (P0) 默认仅 student 可自注册, 教师/管理员账号由 seed 脚本创建.
- P0 阶段: 守卫函数已就绪, 但**未挂接到 auth.py** (见 Task 3 计划).
  调用方应在 register handler 写入数据库前调用 `assert_self_register_role_allowed`.

使用样例:
    >>> from app.services.audit.registration_guard import assert_self_register_role_allowed
    >>> assert_self_register_role_allowed(None)
    'student'
    >>> assert_self_register_role_allowed("student")
    'student'
    >>> try:
    ...     assert_self_register_role_allowed("teacher")
    ... except ValueError as e:
    ...     print("rejected:", e)
    rejected: role 'teacher' is not allowed for self-registration; allowed: ['student']
"""
from __future__ import annotations

ALLOWED_SELF_REGISTER_ROLES: frozenset[str] = frozenset({"student"})


def assert_self_register_role_allowed(role: str | None) -> str:
    """校验自注册角色, 违规抛出 ValueError (由 FastAPI 转为 422).

    Args:
        role: 客户端传入的 role, 允许为 None / 空字符串.

    Returns:
        规范化后的 role (None/空 -> "student").

    Raises:
        ValueError: 角色不在白名单中.
    """
    if role is None or role == "":
        return "student"
    if role not in ALLOWED_SELF_REGISTER_ROLES:
        raise ValueError(
            f"role '{role}' is not allowed for self-registration; "
            f"allowed: {sorted(ALLOWED_SELF_REGISTER_ROLES)}"
        )
    return role
