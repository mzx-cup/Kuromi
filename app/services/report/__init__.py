"""Report 服务命名空间（M5.1）。

当前导出：
  - ParentReportGenerator : 家长月报生成器
  - ParentReport          : 月报数据类
"""
from __future__ import annotations

from app.services.report.parent_report import ParentReport, ParentReportGenerator

__all__ = ["ParentReport", "ParentReportGenerator"]