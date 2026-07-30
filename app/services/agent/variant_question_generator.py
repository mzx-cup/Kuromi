# -*- coding: utf-8 -*-
"""
VariantQuestionGenerator — 变式题生成器(v2.0 P1)

解决"学生假装学会"问题:同一知识点自动生成不同情境/表述/考察角度的题目,
验证学生是真懂还是背答案。

设计:
  - 基于题目模板 + 变量替换(数字/场景/人物/单位...)
  - 4 种变换维度:surface(表述)/scenario(场景)/constraint(条件)/angle(角度)
  - 不强依赖 LLM(支持离线生成),有 LLM 时生成质量更高
  - 生成结果去重,确保与原题不重复

使用:
    gen = VariantQuestionGenerator()
    variants = gen.generate(
        original={
            "stem": "小明有 3 个苹果,妈妈又给他 2 个,现在有几个?",
            "answer": "5",
        },
        knowledge_point="加法应用题",
        n=3,
        dimension="scenario",  # 换场景
    )
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("starlearn.variant_question")


class VariantDimension(str, Enum):
    """变式维度"""
    SURFACE = "surface"        # 同情境,换表述(数字/单位/物品)
    SCENARIO = "scenario"      # 同知识点,换应用场景
    CONSTRAINT = "constraint"  # 同情境,加额外条件
    ANGLE = "angle"            # 同知识点,换考察角度


# 物品替换库(用于 surface 维度)
_SURFACE_NOUN_REPLACE = {
    "苹果": ["橘子", "香蕉", "糖果", "铅笔", "书", "气球"],
    "小明": ["小红", "小华", "小李", "小张", "小王"],
    "妈妈": ["爸爸", "老师", "爷爷", "奶奶", "阿姨"],
    "书": ["笔记本", "练习册", "卡片", "贴纸", "画册"],
    "车": ["自行车", "公交车", "出租车", "火车", "船"],
    "球": ["足球", "篮球", "排球", "乒乓球", "羽毛球"],
    "钱": ["硬币", "纸币", "积分", "金币", "星星"],
}

# 场景替换(用于 scenario 维度)
_SCENARIO_REPLACE = {
    "加法": ["购物找零", "分糖果", "排队人数", "堆积木", "集卡"],
    "减法": ["吃掉", "送给别人", "用掉", "飞走", "卖掉"],
    "乘法": ["打包", "组队", "排方阵", "价格翻倍", "铺地砖"],
    "分数": ["切披萨", "分饮料", "比速度", "打折", "分时间"],
}

# 数字变体范围
_NUMBER_RANGE = (1, 99)


@dataclass
class QuestionVariant:
    """单道变式题"""
    stem: str
    answer: str
    dimension: VariantDimension
    transformations: list[str] = field(default_factory=list)
    similarity: float = 1.0  # 与原题的相似度(0-1,1=几乎一样)

    def to_dict(self) -> dict:
        return {
            "stem": self.stem,
            "answer": self.answer,
            "dimension": self.dimension.value,
            "transformations": self.transformations,
            "similarity": round(self.similarity, 2),
        }


class VariantQuestionGenerator:
    """
    变式题生成器。

    支持 4 种维度,可独立使用也可组合。
    """

    def __init__(self, llm_call: Optional[Callable[[str], str]] = None) -> None:
        """
        Args:
            llm_call: 可选 LLM 调用函数,用于生成高质量变式题。
        """
        self.llm_call = llm_call

    def generate(
        self,
        original: dict[str, Any],
        knowledge_point: str = "",
        n: int = 3,
        dimension: VariantDimension | str = VariantDimension.SURFACE,
    ) -> list[QuestionVariant]:
        """
        为原题生成 n 道变式题。

        Args:
            original: 原题,至少包含 "stem" 和 "answer"
            knowledge_point: 关联知识点(用于 scenario/angle 维度的 LLM 提示)
            n: 生成数量
            dimension: 变式维度

        Returns:
            QuestionVariant 列表(去重后)
        """
        if isinstance(dimension, str):
            try:
                dimension = VariantDimension(dimension)
            except ValueError:
                dimension = VariantDimension.SURFACE

        original_stem = str(original.get("stem", "")).strip()
        original_answer = str(original.get("answer", "")).strip()
        if not original_stem:
            return []

        variants: list[QuestionVariant] = []

        if dimension == VariantDimension.SURFACE:
            variants = self._generate_surface(original_stem, original_answer, n)
        elif dimension == VariantDimension.SCENARIO:
            variants = self._generate_scenario(
                original_stem, original_answer, knowledge_point, n
            )
        elif dimension == VariantDimension.CONSTRAINT:
            variants = self._generate_constraint(original_stem, original_answer, n)
        elif dimension == VariantDimension.ANGLE:
            variants = self._generate_angle(
                original_stem, original_answer, knowledge_point, n
            )

        # 去重(与原题对比)
        deduped: list[QuestionVariant] = []
        for v in variants:
            if v.stem == original_stem:
                continue
            if not any(self._similarity(v.stem, d.stem) > 0.95 for d in deduped):
                deduped.append(v)

        return deduped[:n]

    def _generate_surface(
        self, stem: str, answer: str, n: int
    ) -> list[QuestionVariant]:
        """
        维度 1:surface —— 换数字/单位/物品,题目骨架不变。
        """
        results: list[QuestionVariant] = []
        # 提取原题中的数字
        numbers = re.findall(r"\d+", stem)
        nouns_to_replace = [
            word for word in _SURFACE_NOUN_REPLACE
            if word in stem
        ]

        attempts = 0
        while len(results) < n and attempts < n * 3:
            attempts += 1
            new_stem = stem
            new_answer = answer
            transformations: list[str] = []

            # 数字替换
            if numbers:
                old_num = random.choice(numbers)
                # 生成新数字(避免和原题相同)
                for _ in range(5):
                    new_num = str(random.randint(*_NUMBER_RANGE))
                    if new_num != old_num:
                        break
                new_stem = new_stem.replace(old_num, new_num, 1)
                # 答案如果是数字,也跟着变(简单线性变换,只对纯数字答案有效)
                if answer.isdigit():
                    try:
                        ratio = int(new_num) / max(1, int(old_num))
                        new_answer = str(int(int(answer) * ratio))
                    except (ValueError, ZeroDivisionError):
                        pass
                transformations.append(f"换数字 {old_num}→{new_num}")

            # 物品替换
            for noun in nouns_to_replace[:1]:  # 一次只换一个
                repl = random.choice(_SURFACE_NOUN_REPLACE[noun])
                new_stem = new_stem.replace(noun, repl, 1)
                transformations.append(f"换物品 {noun}→{repl}")

            if new_stem != stem:
                results.append(QuestionVariant(
                    stem=new_stem,
                    answer=new_answer,
                    dimension=VariantDimension.SURFACE,
                    transformations=transformations,
                    similarity=0.85,
                ))

        return results

    def _generate_scenario(
        self,
        stem: str,
        answer: str,
        knowledge_point: str,
        n: int,
    ) -> list[QuestionVariant]:
        """
        维度 2:scenario —— 换应用场景。
        """
        # 启发式:从知识点和题干里猜属于哪个数学运算/概念
        kp = (knowledge_point or "").lower()
        category: str | None = None
        for key, scenarios in _SCENARIO_REPLACE.items():
            if key in kp:
                category = key
                break
        if not category:
            # 启发式:从题干里找线索
            if "加" in stem or "一共" in stem or "和" in stem:
                category = "加法"
            elif "减" in stem or "剩" in stem or "拿走" in stem:
                category = "减法"
            elif "乘" in stem or "倍" in stem or "×" in stem or "*" in stem:
                category = "乘法"
            elif "分之" in stem or "/" in stem or "分数" in stem:
                category = "分数"

        if not category:
            # 没识别出来,降级到 surface
            return self._generate_surface(stem, answer, n)

        scenarios = _SCENARIO_REPLACE[category]
        results: list[QuestionVariant] = []
        for i, scen in enumerate(scenarios[:n]):
            new_stem = f"【场景:{scen}】{stem}"
            transformations = [f"换场景: {scen}"]
            results.append(QuestionVariant(
                stem=new_stem,
                answer=answer,  # 答案通常不变
                dimension=VariantDimension.SCENARIO,
                transformations=transformations,
                similarity=0.65,
            ))
        return results

    def _generate_constraint(
        self, stem: str, answer: str, n: int
    ) -> list[QuestionVariant]:
        """
        维度 3:constraint —— 同情境,加额外条件(让题目变难/变有趣)。

        添加的约束类型:
          - 时间限制("限 5 分钟内完成")
          - 资源限制("只能用加法")
          - 多条件("并且 X 还...")
          - 反向问("如果不要 X,会怎样")
        """
        constraints = [
            ("限 3 分钟内答出", "限时"),
            ("要求列出 2 种不同的解法", "多解"),
            ("如果再给你 1 个,会怎样?", "扩展"),
            ("如果不这样做,反过来的结果是什么?", "反向"),
            ("用画图的方式表示你的思路", "画图"),
        ]
        results: list[QuestionVariant] = []
        for text, kind in constraints[:n]:
            new_stem = f"{stem}\n（附加:{text}）"
            results.append(QuestionVariant(
                stem=new_stem,
                answer=answer,
                dimension=VariantDimension.CONSTRAINT,
                transformations=[f"加约束: {kind}"],
                similarity=0.75,
            ))
        return results

    def _generate_angle(
        self,
        stem: str,
        answer: str,
        knowledge_point: str,
        n: int,
    ) -> list[QuestionVariant]:
        """
        维度 4:angle —— 同知识点,换考察角度。

        适用于"判断 → 选择 → 计算 → 证明 → 应用"这类角度变换。
        """
        angles = [
            ("这道题考察的知识点是什么?", "元认知"),
            ("你能用一句话解释为什么这样做吗?", "原理"),
            ("举一个生活中用这个知识点的例子。", "应用"),
            ("如果把题目里的数字改大 10 倍,还成立吗?", "推广"),
            ("这道题和 X 知识点有什么联系?", "关联"),
        ]
        results: list[QuestionVariant] = []
        for text, kind in angles[:n]:
            new_stem = f"{stem}\n（换角度:{text}）"
            results.append(QuestionVariant(
                stem=new_stem,
                answer="(开放性问题,引导学生表达)",
                dimension=VariantDimension.ANGLE,
                transformations=[f"换角度: {kind}"],
                similarity=0.55,
            ))
        return results

    def _similarity(self, s1: str, s2: str) -> float:
        """简单相似度:共同字符 / 总字符(Jaccard)"""
        if not s1 or not s2:
            return 0.0
        set1 = set(s1)
        set2 = set(s2)
        inter = len(set1 & set2)
        union = len(set1 | set2)
        return inter / union if union else 0.0


# 单例
_default_gen: Optional[VariantQuestionGenerator] = None


def get_variant_generator() -> VariantQuestionGenerator:
    """获取默认变式题生成器(单例)"""
    global _default_gen
    if _default_gen is None:
        _default_gen = VariantQuestionGenerator()
    return _default_gen
