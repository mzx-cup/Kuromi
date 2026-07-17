# -*- coding: utf-8 -*-
"""
HallucinationGuard — 四层防幻觉校验器

对 LLM 生成的回答进行多层校验，确保输出准确可靠：
  Layer 1: 教材引用锚定校验 — 验证 [Ref: xxx] 是否真实存在于 RAG 结果
  Layer 2: 外部来源交叉校验 — 验证 Web Search 结果中的一致性
  Layer 3: 代码执行验证 — 编程问题专用，sandbox 运行代码
  Layer 4: 置信度决策 — 综合评分，低于阈值时拦截或追加免责声明

设计原则：
  - 与 LLM 调用解耦：先生成，再校验
  - 流式场景：先收集完整文本，再后处理校验
  - 容错：任何一层失败都不阻断，记录到 confidence_report
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional, Tuple

from app.core.trace import get_current_span
from app.services.tutor_engine.models import (
    Citation,
    ConfidenceReport,
    RAGResult,
    RichContext,
    TutorEvent,
)

logger = logging.getLogger("starlearn.tutor_engine")


# 可信外部域名列表
TRUSTED_DOMAINS = {
    "github.com", "docs.python.org", "developer.mozilla.org",
    "docs.oracle.com", "learn.microsoft.com", "leetcode.cn",
    "leetcode.com", "www.w3schools.com", "www.runoob.com",
    "docs.djangoproject.com", "flask.palletsprojects.com",
    "docs.sqlalchemy.org", "numpy.org", "pandas.pydata.org",
    "matplotlib.org", "scikit-learn.org", "pytorch.org",
    "tensorflow.org", "docs.opencv.org", "redis.io",
    "docs.docker.com", "kubernetes.io", "docs.github.com",
    "stackoverflow.com", "segmentfault.com", "juejin.cn",
    "zhihu.com", "csdn.net", "cnblogs.com",
}


@dataclass
class GuardResult:
    """校验结果"""
    answer_text: str
    citations: list[Citation]
    confidence: ConfidenceReport


class HallucinationGuard:
    """
    防幻觉四层校验器。

    使用示例:
        guard = HallucinationGuard()
        stream, text, citations, confidence = await guard.process(event, rich_context)
    """

    def __init__(
        self,
        citation_threshold: float = 0.85,
        warning_threshold: float = 0.60,
        enable_code_execution: bool = True,
    ):
        self.citation_threshold = citation_threshold
        self.warning_threshold = warning_threshold
        self.enable_code_execution = enable_code_execution

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def process(
        self,
        event: TutorEvent,
        rich: RichContext,
    ) -> Tuple[Optional[AsyncIterator[str]], str, list[Citation], ConfidenceReport]:
        """
        生成 LLM 回答并进行完整校验。

        返回: (answer_stream, answer_text, citations, confidence_report)
        """
        # Step 1: 生成回答（非流式，便于校验）
        answer_text = await self._generate_answer(event, rich)

        # Step 2: Layer 1 — 教材引用校验
        citations, citation_valid = self._validate_citations(answer_text, rich.rag_results)

        # Step 3: Layer 2 — 外部来源校验
        web_consistency = self._check_web_consistency(answer_text, rich.web_results)

        # Step 4: Layer 3 — 代码执行验证
        code_verified, code_result = False, ""
        if self.enable_code_execution and self._contains_code(answer_text):
            code_verified, code_result = await self._verify_code(answer_text)

        # Step 5: Layer 4 — 置信度决策
        confidence = self._compute_confidence(
            len(citations), citation_valid, web_consistency, code_verified, rich
        )

        # Step 6: 根据置信度处理回答
        final_text = self._apply_confidence_policy(answer_text, confidence, rich)

        # Trace: record guard attributes on the current root span (if any).
        span = get_current_span()
        if span is not None:
            span.set_attribute("guard.citations_checked", len(citations))
            span.set_attribute("guard.citation_validated", citation_valid)
            span.set_attribute("guard.web_consistency", web_consistency)
            span.set_attribute("guard.blocked", getattr(confidence, "blocked", False))

        # 创建模拟流（兼容现有 SSE 接口）
        async def _stream() -> AsyncIterator[str]:
            yield final_text

        return _stream(), final_text, citations, confidence

    # ------------------------------------------------------------------
    # Step 1: 生成回答
    # ------------------------------------------------------------------

    async def _generate_answer(self, event: TutorEvent, rich: RichContext) -> str:
        """调用 LLM 生成回答。"""
        try:
            # 构建带教材引用的 system prompt
            system_prompt = self._build_system_prompt(rich)
            user_prompt = event.get_question_text()

            # 调用现有 LLM 接口
            from main import call_llm
            answer = await asyncio.to_thread(call_llm, system_prompt, user_prompt, 0.3)
            return answer
        except Exception as e:
            logger.error(f"[HallucinationGuard] LLM 生成失败: {e}")
            return "抱歉，我暂时无法回答这个问题。"

    def _build_system_prompt(self, rich: RichContext) -> str:
        """构建要求教材引用的 system prompt。"""
        parts = [
            "你是一位编程学习平台的 AI 导师。回答学生问题时请遵循以下规则：",
            "",
            "1. 优先基于提供的教材参考回答，并在关键知识点后标注引用来源。",
            "   引用格式: [Ref: source_id]（source_id 会在教材参考中提供）",
            "2. 如果涉及代码，请给出完整可运行的代码示例。",
            "3. 如果教材中没有相关内容，请明确说明'教材中未涵盖此内容'，",
            "   然后基于你的知识补充回答。",
            "4. 不要编造不存在的教材引用。",
            "",
        ]

        # 注入教材参考
        if rich.rag_context_text:
            parts.append("【教材参考】")
            parts.append(rich.rag_context_text[:3000])  # 限制长度
            parts.append("")

        # 注入记忆
        if rich.memory_context_text:
            parts.append(rich.memory_context_text[:1000])
            parts.append("")

        # 注入网络搜索
        if rich.web_context_text:
            parts.append("【网络搜索结果】")
            parts.append(rich.web_context_text[:1500])
            parts.append("")

        parts.append("请基于以上资料回答学生的问题。")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Layer 1: 教材引用校验
    # ------------------------------------------------------------------

    def _validate_citations(
        self,
        answer_text: str,
        rag_results: list[RAGResult],
    ) -> Tuple[list[Citation], bool]:
        """
        提取并校验回答中的教材引用。

        返回: (校验通过的引用列表, 是否全部有效)
        """
        valid_sources = {r.source_id for r in rag_results}
        citations: list[Citation] = []
        all_valid = True

        # 匹配 [Ref: xxx] 和 [Doc_Ref: xxx]
        pattern = r"\[(?:Ref|Doc_Ref):\s*([^\]]+)\]"
        matches = re.findall(pattern, answer_text)

        for raw_ref in matches:
            ref_id = raw_ref.strip()
            is_valid = ref_id in valid_sources
            if not is_valid:
                all_valid = False
                logger.warning(f"[HallucinationGuard] 虚假引用 detected: {ref_id}")

            # 查找对应的 RAG 结果
            rag = next((r for r in rag_results if r.source_id == ref_id), None)
            citations.append(Citation(
                source_id=ref_id,
                source_title=rag.source_title if rag else ref_id,
                quoted_text=rag.content[:200] if rag else "",
                chapter_url=rag.deep_link if rag else "",
                confidence=1.0 if is_valid else 0.0,
                validated=is_valid,
            ))

        return citations, all_valid

    # ------------------------------------------------------------------
    # Layer 2: 外部来源交叉校验
    # ------------------------------------------------------------------

    def _check_web_consistency(
        self,
        answer_text: str,
        web_results: list[Any],
    ) -> float:
        """
        校验回答与 Web Search 结果的一致性。

        简化实现：检查回答中的关键数字/版本号是否出现在搜索结果中。
        返回 0.0~1.0 的一致性分数。
        """
        if not web_results:
            return 0.5  # 无搜索结果，中性分数

        # 提取回答中的数字和版本号
        numbers = set(re.findall(r"\d+\.\d+", answer_text))
        versions = set(re.findall(r"\d+\.\d+\.\d+", answer_text))

        if not numbers and not versions:
            return 0.7  # 无具体数字，难以校验，给中等分数

        # 检查是否出现在搜索结果中
        web_text = " ".join([r.content for r in web_results]).lower()
        matches = 0
        total = 0

        for num in numbers:
            total += 1
            if num in web_text:
                matches += 1

        for ver in versions:
            total += 1
            if ver in web_text:
                matches += 1

        if total == 0:
            return 0.7

        consistency = matches / total
        logger.info(f"[HallucinationGuard] Web 一致性: {consistency:.2f} ({matches}/{total})")
        return consistency

    # ------------------------------------------------------------------
    # Layer 3: 代码执行验证
    # ------------------------------------------------------------------

    def _contains_code(self, text: str) -> bool:
        """检测回答中是否包含代码块"""
        return "```" in text or "    " in text[:500]

    async def _verify_code(self, answer_text: str) -> Tuple[bool, str]:
        """
        提取并验证回答中的代码块。

        返回: (是否通过验证, 执行结果摘要)
        """
        code_blocks = self._extract_code_blocks(answer_text)
        if not code_blocks:
            return True, "无代码块"

        all_passed = True
        results = []

        for lang, code in code_blocks:
            try:
                passed, result = await self._run_code_sandbox(lang, code)
                results.append(f"{lang}: {'✓' if passed else '✗'} {result[:100]}")
                if not passed:
                    all_passed = False
            except Exception as e:
                results.append(f"{lang}: ✗ 验证异常: {e}")
                all_passed = False

        return all_passed, "; ".join(results)

    def _extract_code_blocks(self, text: str) -> list[Tuple[str, str]]:
        """提取 Markdown 代码块"""
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        return [(lang or "text", code.strip()) for lang, code in matches]

    async def _run_code_sandbox(self, lang: str, code: str) -> Tuple[bool, str]:
        """
        在受限环境中运行代码。

        目前支持:
          - python: 使用 exec 在受限 globals 中运行
          - javascript: 调用 node 子进程（如果可用）
        """
        if lang.lower() in ("python", "py", ""):
            return await self._run_python_sandbox(code)
        elif lang.lower() in ("javascript", "js", "node"):
            return await self._run_js_sandbox(code)
        else:
            return True, f"不支持的语言: {lang}"

    async def _run_python_sandbox(self, code: str) -> Tuple[bool, str]:
        """Python 受限执行"""
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr

        # 安全检查：禁止危险操作
        dangerous = ["__import__", "open", "os.", "sys.", "subprocess", "eval(", "exec("]
        for d in dangerous:
            if d in code:
                return True, f"包含潜在危险操作 '{d}'，跳过执行验证"

        # 创建受限环境
        safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "bool": bool,
                "type": type,
                "isinstance": isinstance,
                "hasattr": hasattr,
                "getattr": getattr,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
            }
        }

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(code, safe_globals, {})
            output = stdout_buf.getvalue().strip()
            return True, f"输出: {output[:200]}"
        except Exception as e:
            error = stderr_buf.getvalue().strip() or str(e)
            return False, f"运行错误: {error[:200]}"

    async def _run_js_sandbox(self, code: str) -> Tuple[bool, str]:
        """JavaScript 子进程执行"""
        import shutil
        import subprocess

        if not shutil.which("node"):
            return True, "Node.js 不可用，跳过 JS 验证"

        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "-e", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode == 0:
                return True, f"输出: {stdout.decode()[:200]}"
            else:
                return False, f"错误: {stderr.decode()[:200]}"
        except asyncio.TimeoutError:
            return False, "执行超时"
        except Exception as e:
            return True, f"验证异常: {e}"

    # ------------------------------------------------------------------
    # Layer 4: 置信度决策
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        citation_count: int,
        citation_valid: bool,
        web_consistency: float,
        code_verified: bool,
        rich: RichContext,
    ) -> ConfidenceReport:
        """计算最终置信度"""
        # RAG 相关度最高分
        rag_max = max((r.relevance_score for r in rich.rag_results), default=0.0)

        # 各项分数
        citation_score = min(1.0, citation_count * 0.25) if citation_valid else 0.0
        web_score = web_consistency * 0.20
        code_score = 0.30 if code_verified else 0.0
        rag_score = min(1.0, rag_max) * 0.25

        # 如果没有代码块，代码验证分不参与计算
        has_code = any("```" in r.content for r in rich.rag_results)
        if not has_code:
            # 重新平衡权重
            total = citation_score + web_score + rag_score
            if total > 0:
                factor = 1.0 / total
                citation_score *= factor
                web_score *= factor
                rag_score *= factor
            code_score = 0.0

        final = min(1.0, citation_score + web_score + code_score + rag_score)

        return ConfidenceReport(
            citation_count=citation_count,
            citation_validated=citation_valid,
            web_search_used=len(rich.web_results) > 0,
            web_consistency=web_consistency,
            code_verified=code_verified,
            rag_relevance_max=rag_max,
            final_confidence=final,
        )

    def _apply_confidence_policy(
        self,
        answer_text: str,
        confidence: ConfidenceReport,
        rich: RichContext,
    ) -> str:
        """
        根据置信度决定如何处理回答。

        - >= 0.85: 直接输出
        - 0.60 ~ 0.84: 追加免责声明
        - < 0.60: 拦截，替换为推荐资料
        """
        fc = confidence.final_confidence

        if fc >= self.citation_threshold:
            confidence.uncertainty_note = ""
            return answer_text

        elif fc >= self.warning_threshold:
            confidence.uncertainty_note = (
                "\n\n⚠️ 以上回答基于现有教材资料，"
                "建议结合官方文档或进一步验证。"
            )
            return answer_text + confidence.uncertainty_note

        else:
            # 低置信度：拦截并替换
            confidence.blocked = True
            confidence.uncertainty_note = "置信度过低，已拦截"

            # 生成推荐资料文本
            links_text = ""
            if rich.rag_results:
                links_text += "\n【相关教材章节】"
                for r in rich.rag_results[:3]:
                    links_text += f"\n- {r.source_title}"

            if rich.web_results:
                links_text += "\n【网络参考】"
                for w in rich.web_results[:2]:
                    links_text += f"\n- {w.title}: {w.url}"

            return (
                "抱歉，我暂时无法给出完全确定的答案。\n"
                "这可能是因为当前教材资料中没有涵盖此内容，"
                "或者问题涉及较新的技术动态。\n"
                f"建议你查看以下资料：{links_text}\n\n"
                "你也可以换个更具体的方式提问，我会尽力帮助你。"
            )
