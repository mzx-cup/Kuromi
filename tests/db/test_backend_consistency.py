"""Split-brain 回归测试 — 钉死后端 + 启动期一致性校验。

背景：历史上 ``STARLEARN_DB_BACKEND`` 默认 ``auto``，导致同一进程的不
同功能在 MySQL / SQLite 之间"猜"到不同引擎，把数据写散到两个库里，事
后无法对账（"为什么刚写入的数据查不到"）。修复方案：

1. 生产配置（``config/.env``）与比赛启动脚本（``scripts/start_competition.sh``）
   都显式钉死 ``STARLEARN_DB_BACKEND=sqlite``；
2. ``main.py`` lifespan 启动时调用 ``db.verify_backend_consistency()`` 做
   连通性自检（SELECT 1），连不上直接 raise —— 进程拒绝带坏配置运行。

这套测试固化上述契约，任何一项被改回去都立即失败：

- ``test_*`` 静态契约：env / shell / main.py 源码必须仍然包含钉死语句
  与 lifespan 调用点；
- ``test_verify_*`` 运行时契约：``verify_backend_consistency()`` 必须
  在 sqlite 健康时返回 ok，在 sqlite 不可用时 raise ``BackendUnavailable``
  （不静默降级到 json）。

注：所有运行时用例通过 monkeypatch 局部改写 ``db.DB_BACKEND`` /
``db.SQLITE_PATH`` / ``db._detect_backend`` 等，避免污染会话级临时库。
"""
from __future__ import annotations

from pathlib import Path

import pytest

import db
from db import BackendUnavailable


# ──────────────────────────────────────────────────────────────────────
# 静态契约 — 文件内容层
# ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestProductionConfigPinsSqlite:
    """``config/.env`` 必须显式钉死 sqlite —— auto 会导致引擎分裂。"""

    def test_env_file_pins_sqlite(self):
        env_text = (REPO_ROOT / "config" / ".env").read_text(encoding="utf-8")
        # 找到 STARLEARN_DB_BACKEND=... 这一行（注释里也可能出现）
        lines = [
            ln.strip()
            for ln in env_text.splitlines()
            if ln.strip().startswith("STARLEARN_DB_BACKEND=")
            and not ln.strip().startswith("#")
        ]
        assert lines, "config/.env missing STARLEARN_DB_BACKEND= line"
        # 至少有一个有效行 === sqlite
        assert any(
            ln.endswith("=sqlite") for ln in lines
        ), f"config/.env must pin STARLEARN_DB_BACKEND=sqlite, found: {lines}"

    def test_env_file_explains_why_not_auto(self):
        """防回归：注释里必须保留"为什么不用 auto"的说明，防止下个工程师
        手贱改回 auto。"""
        env_text = (REPO_ROOT / "config" / ".env").read_text(encoding="utf-8")
        assert "auto" in env_text, (
            "config/.env should document why auto is forbidden "
            "(split-brain data divergence)"
        )


class TestCompetitionScriptPinsSqlite:
    """``scripts/start_competition.sh`` 必须把 sqlite 设为默认值，
    与 config/.env 对齐；切 MySQL 需显式传环境变量。"""

    def test_script_pins_sqlite_default(self):
        script = (REPO_ROOT / "scripts" / "start_competition.sh").read_text(
            encoding="utf-8"
        )
        # 必须出现 ``export STARLEARN_DB_BACKEND="${STARLEARN_DB_BACKEND:-sqlite}"``
        # 或者等价的 sqlite 默认值。
        assert "STARLEARN_DB_BACKEND" in script
        assert "sqlite" in script, (
            "scripts/start_competition.sh must default STARLEARN_DB_BACKEND to sqlite"
        )

    def test_script_does_not_default_to_auto(self):
        script = (REPO_ROOT / "scripts" / "start_competition.sh").read_text(
            encoding="utf-8"
        )
        # 防回归：默认值不能是 auto
        assert "${STARLEARN_DB_BACKEND:-auto}" not in script, (
            "scripts/start_competition.sh must NOT default to auto "
            "(split-brain risk in competition mode)"
        )


class TestLifespanCallsVerifyBackendConsistency:
    """``main.py`` 的 lifespan 启动 hook 必须调用 verify_backend_consistency()
    —— 进程拒绝带着坏配置运行，否则又会回到"静默写散"的老路。"""

    def test_main_py_lifespan_invokes_verify(self):
        main_text = (REPO_ROOT / "main.py").read_text(encoding="utf-8")
        # 必须同时出现 lifespan 定义与 verify_backend_consistency 调用
        assert "async def lifespan" in main_text
        assert "verify_backend_consistency" in main_text
        # 调用必须在 lifespan 函数体内（粗略检查：lifespan 之内）
        lifespan_start = main_text.index("async def lifespan")
        lifespan_body = main_text[lifespan_start:]
        assert "verify_backend_consistency" in lifespan_body

    def test_lifespan_runs_before_init_db(self):
        """verify_backend_consistency() 必须在 init_db() 之前 —— 否则又
        会带着坏连接跑到一半才发现。"""
        main_text = (REPO_ROOT / "main.py").read_text(encoding="utf-8")
        lifespan_start = main_text.index("async def lifespan")
        # 截到第一个 yield 之前（启动段）
        yield_idx = main_text.index("yield", lifespan_start)
        startup = main_text[lifespan_start:yield_idx]
        verify_pos = startup.index("verify_backend_consistency")
        init_pos = startup.index("init_db")
        assert verify_pos < init_pos, (
            "verify_backend_consistency() must run BEFORE init_db() in lifespan"
        )


# ──────────────────────────────────────────────────────────────────────
# 运行时契约 — verify_backend_consistency() 行为
# ──────────────────────────────────────────────────────────────────────

class TestVerifyBackendConsistencyBehavior:
    """``verify_backend_consistency()`` 必须真的连一次 SELECT 1，
    而不是走过场；连不上必须 raise（不静默切到 json）。"""

    def test_returns_ok_for_healthy_sqlite(self, tmp_path, monkeypatch):
        db_file = tmp_path / "healthy.db"
        # 让 db.py 走我们这条隔离的临时库 + 显式 sqlite
        monkeypatch.setattr(db, "DB_BACKEND", "sqlite")
        monkeypatch.setattr(db, "SQLITE_PATH", str(db_file))
        # 重置缓存的 effective_backend，强制重探测
        monkeypatch.setattr(db, "_effective_backend", None)

        info = db.verify_backend_consistency()

        assert info["configured_backend"] == "sqlite"
        assert info["effective_backend"] == "sqlite"
        assert info["connectivity"] == "ok"
        assert info["sqlite_path"] == str(db_file)
        # ORM 引擎摘要应可读（即便有 mismatch 也不阻断）
        assert "orm_database_url" in info

    def test_raises_when_sqlite_unavailable(self, tmp_path, monkeypatch):
        """把 SQLite_PATH 指向一个无法创建的目录（路径冲突），open_effective_connection
        必须抛 BackendUnavailable —— 而不是悄悄 yield None 走 json 分支。"""
        # 在 Linux/Windows 上都能复现：父目录不存在 + 显式传一个 file flag 不可能成功
        impossible = tmp_path / "no_such_dir" / "x.db"
        monkeypatch.setattr(db, "DB_BACKEND", "sqlite")
        monkeypatch.setattr(db, "SQLITE_PATH", str(impossible))
        monkeypatch.setattr(db, "_effective_backend", None)

        # open_effective_connection 在 _open_sqlite 失败时抛 BackendUnavailable
        with pytest.raises(BackendUnavailable) as exc_info:
            db.open_effective_connection()
        assert "sqlite" in str(exc_info.value.backend)
        # 同理 verify_backend_consistency() 也必须抛，不能 return
        with pytest.raises(BackendUnavailable):
            db.verify_backend_consistency()

    def test_does_not_silently_fall_back_to_json(self, tmp_path, monkeypatch):
        """生效后端 sqlite 不可用时，绝不能悄悄切到 json（那样又回到
        老 split-brain 形态：部分调用写 SQL、部分调用写 JSON 文件）。"""
        impossible = tmp_path / "no_such_dir" / "x.db"
        monkeypatch.setattr(db, "DB_BACKEND", "sqlite")
        monkeypatch.setattr(db, "SQLITE_PATH", str(impossible))
        monkeypatch.setattr(db, "_effective_backend", None)

        # 捕获 BackendUnavailable，确认 effective_backend 没有被偷偷改成 json
        with pytest.raises(BackendUnavailable):
            db.open_effective_connection()
        # 即便 _effective_backend 被缓存，也不能是 json
        if db._effective_backend is not None:
            assert db._effective_backend != "json", (
                "open_effective_connection must not silently downgrade to JSON"
            )

    def test_auto_mode_logs_warning(self, tmp_path, monkeypatch, capsys):
        """``STARLEARN_DB_BACKEND=auto`` 必须打印告警（提示操作者改回显式
        值），不能默默接受。"""
        db_file = tmp_path / "auto.db"
        monkeypatch.setattr(db, "DB_BACKEND", "auto")
        monkeypatch.setattr(db, "SQLITE_PATH", str(db_file))
        monkeypatch.setattr(db, "_effective_backend", None)

        db.verify_backend_consistency()

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "auto" in combined.lower(), (
            "verify_backend_consistency() must warn when STARLEARN_DB_BACKEND=auto"
        )
        # 提示应当指向 config/.env
        assert "config/.env" in combined or "STARLEARN_DB_BACKEND" in combined

    def test_explicit_sqlite_pin_does_not_warn_auto(self, tmp_path, monkeypatch, capsys):
        """显式 sqlite 钉死后，告警应消失（仅 auto 才打）。"""
        db_file = tmp_path / "pinned.db"
        monkeypatch.setattr(db, "DB_BACKEND", "sqlite")
        monkeypatch.setattr(db, "SQLITE_PATH", str(db_file))
        monkeypatch.setattr(db, "_effective_backend", None)

        db.verify_backend_consistency()

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "STARLEARN_DB_BACKEND=auto" not in combined, (
            "explicit STARLEARN_DB_BACKEND=sqlite should not emit auto warning"
        )