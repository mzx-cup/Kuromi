# -*- coding: utf-8 -*-
"""
PPT 生成服务
"""

from app.services.ppt.types import (
    PPTGenerationRequest,
    PPTGenerationResult,
)
from app.services.ppt.minimax import get_ppt_provider

__all__ = [
    "PPTGenerationRequest",
    "PPTGenerationResult",
    "get_ppt_provider",
]
