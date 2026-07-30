"""Safety 服务命名空间（M3.2）。

当前导出：
  - JailbreakDetector  : 越狱检测（L0 正则 + L1 LLM 占位）
  - JailbreakResult    : 风险评估结果 dataclass

未来扩展：
  - 内容安全分类（涉政/涉暴/色情）
  - 隐私信息脱敏
"""
from __future__ import annotations

from app.services.safety.jailbreak_detector import JailbreakDetector, JailbreakResult

__all__ = ["JailbreakDetector", "JailbreakResult"]