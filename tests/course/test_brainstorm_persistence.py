"""Tests for brainstorm session persistence (M3.8).

验证:
  - save + load 跨"重启"（新实例）仍能恢复 session
  - JSONL 文件持久化在 SAVE_DIR 下可被发现
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_storage_dir():
    """临时目录，测试结束后清理。"""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.asyncio
async def test_brainstorm_session_persists_across_restart(temp_storage_dir):
    """save → simulate restart (新模块实例) → load 必须能恢复。"""
    from app.services import course_brainstorm
    from app.services.course_brainstorm import BrainstormState, _save, _load

    # 用临时 JSONL 文件替换默认持久化路径
    test_file = temp_storage_dir / "brainstorm.jsonl"
    with patch.object(course_brainstorm, "_PERSIST_FILE", test_file):
        # 创建 + 保存
        state = BrainstormState(
            brainstorm_id="bs_test_1",
            student_id="u1",
            requirement="Python 入门",
        )
        await _save(state)

        # 模拟重启：清空内存 + 重载
        course_brainstorm.BRAINSTORM_STORE.clear()
        await course_brainstorm._rehydrate()

        # 必须能恢复
        restored = await _load("bs_test_1")
        assert restored.student_id == "u1"
        assert restored.requirement == "Python 入门"


@pytest.mark.asyncio
async def test_brainstorm_persistence_file_contains_valid_jsonl(temp_storage_dir):
    """持久化文件必须是合法 JSONL。"""
    from app.services import course_brainstorm
    from app.services.course_brainstorm import BrainstormState, _save

    test_file = temp_storage_dir / "brainstorm.jsonl"
    with patch.object(course_brainstorm, "_PERSIST_FILE", test_file):
        state = BrainstormState(
            brainstorm_id="bs_test_2",
            student_id="u2",
            requirement="代数基础",
        )
        await _save(state)

        # 文件必须存在 + 每行是合法 JSON
        assert test_file.exists()
        with test_file.open("r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        assert len(lines) >= 1
        for line in lines:
            obj = json.loads(line)
            assert "brainstorm_id" in obj
            assert "student_id" in obj