"""Repository 命名空间.

P0 阶段: 仅暴露 `DemoRepository` 骨架.
P1 阶段: 把 db.py 中散落的 demo 访问函数迁入此命名空间,
         `app/api/demo_path.py` 仅通过 Repository 读写数据.
"""
from app.services.repository.demo_repo import DemoRepository  # noqa: F401

__all__ = ["DemoRepository"]
