from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Awaitable, Optional

from state import (
    AgentStepLog,
    ChatMessage,
    ContentType,
    DialogueRole,
    DialogueType,
    DifficultyLevel,
    EmotionType,
    GeneratorOutput,
    LearningProfile,
    PathNode,
    PlannerOutput,
    ResourceLink,
    StudentState,
)


class BaseAgent(ABC):
    name: str = "base_agent"
    role: str = "base"
    description: str = ""

    @abstractmethod
    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        ...

    def _create_log(
        self,
        input_summary: str,
        output_summary: str,
        processing_time_ms: int,
        status: str = "success",
        error_message: str = "",
    ) -> AgentStepLog:
        return AgentStepLog(
            agent_name=self.name,
            agent_role=self.role,
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            processing_time_ms=processing_time_ms,
            status=status,
            error_message=error_message,
            timestamp=datetime.now(),
        )


class ProfilerAgent(BaseAgent):
    name = "profiler"
    role = "画像分析智能体"
    description = "分析学生输入与遥测数据，更新6维学情画像，识别对话类型和情绪状态，检测认知超载"

    OVERLOAD_SCORE_THRESHOLD = 75
    OVERLOAD_CRITICAL_THRESHOLD = 90
    HIGH_DWELL_THRESHOLD = 120
    HIGH_ENTROPY_THRESHOLD = 65
    FAST_SCROLL_THRESHOLD = 300

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        user_input = state.get_recent_messages(1)
        input_text = user_input[0].content if user_input else ""

        try:
            profile_update, dialogue_type, keywords, emotion = await self._analyze(input_text, state.profile)

            telemetry_overload = self._analyze_telemetry(state)
            if telemetry_overload["is_overloaded"]:
                emotion = (
                    EmotionType.CONFUSED,
                    max(emotion[1], telemetry_overload["intensity"]),
                    telemetry_overload["reason"],
                )
                dialogue_type = "confusion"
                state.metadata["cognitive_overload"] = True
                state.metadata["overload_score"] = telemetry_overload["score"]
                state.metadata["overload_intervention"] = telemetry_overload["intervention"]

            state.profile = self._merge_profile(state.profile, profile_update)
            state.update_emotion(emotion[0], emotion[1], emotion[2])
            state.add_message(DialogueRole.PROFILER, f"画像更新完成 | 对话类型: {dialogue_type} | 关键词: {keywords}")
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                f"分析输入: {input_text[:100]}",
                f"对话类型={dialogue_type}, 情绪={emotion[0]}, 关键词={keywords}, 遥测超载={telemetry_overload['is_overloaded']}",
                elapsed
            ))
            state.metadata = {**state.metadata, "dialogue_type": dialogue_type, "search_keywords": keywords}
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                f"分析输入: {input_text[:100]}", "", elapsed, "error", str(e)
            ))
        return state

    def _analyze_telemetry(self, state: StudentState) -> dict[str, Any]:
        result = {
            "is_overloaded": False,
            "score": 0,
            "intensity": 0.5,
            "reason": "",
            "intervention": "",
        }

        telemetry = state.telemetry_data
        if not telemetry:
            return result

        overload_data = telemetry.get("overload", {})
        overload_score = overload_data.get("current_score", 0)
        overload_triggered = overload_data.get("triggered", False)

        zone_dwell = telemetry.get("zone_dwell_times", {})
        max_zone_dwell = max(zone_dwell.values()) if zone_dwell else 0

        mouse_metrics = telemetry.get("mouse_metrics", {})
        mouse_entropy = mouse_metrics.get("path_entropy", 0)

        scroll_metrics = telemetry.get("scroll_metrics", {})
        avg_scroll_speed = scroll_metrics.get("avg_speed", 0)

        computed_score = overload_score
        if computed_score == 0:
            dwell_score = min(100, (max_zone_dwell / self.HIGH_DWELL_THRESHOLD) * 50) if max_zone_dwell > 0 else 0
            entropy_score = min(100, (mouse_entropy / self.HIGH_ENTROPY_THRESHOLD) * 50) if mouse_entropy > 0 else 0
            scroll_score = min(100, (avg_scroll_speed / self.FAST_SCROLL_THRESHOLD) * 30) if avg_scroll_speed > self.FAST_SCROLL_THRESHOLD else 0
            computed_score = dwell_score * 0.40 + entropy_score * 0.35 + scroll_score * 0.25

        result["score"] = round(computed_score)

        if computed_score >= self.OVERLOAD_SCORE_THRESHOLD or overload_triggered:
            result["is_overloaded"] = True
            result["intensity"] = min(1.0, computed_score / 100)

            if computed_score >= self.OVERLOAD_CRITICAL_THRESHOLD:
                result["reason"] = f"认知超载严重(得分{computed_score:.0f}): 长时间停留+鼠标无规律+滚动异常"
                result["intervention"] = (
                    "⚠️ 检测到您在此处停留较久且出现认知疲劳迹象，"
                    "是否需要为您生成一个更基础的先导比喻来帮助理解？"
                    "或者我们可以先切换到更简单的相关知识点？"
                )
            elif max_zone_dwell > self.HIGH_DWELL_THRESHOLD:
                result["reason"] = f"区域停留时间过长({max_zone_dwell:.0f}秒), 超载得分{computed_score:.0f}"
                result["intervention"] = (
                    "💡 检测到您在此处停留较久，"
                    "是否需要用一个生活中的比喻来帮助理解这个概念？"
                )
            elif mouse_entropy > self.HIGH_ENTROPY_THRESHOLD:
                result["reason"] = f"鼠标轨迹无规律(熵值{mouse_entropy}), 超载得分{computed_score:.0f}"
                result["intervention"] = (
                    "🤔 看起来您可能在寻找关键信息，"
                    "需要我为您标注这段内容的核心要点吗？"
                )
            else:
                result["reason"] = f"遥测综合超载得分{computed_score:.0f}"
                result["intervention"] = (
                    "💭 检测到学习状态异常，"
                    "是否需要换个更直观的方式来理解当前内容？"
                )

        return result

    async def _analyze(
        self, text: str, profile: LearningProfile
    ) -> tuple[dict[str, Any], str, list[str], tuple[EmotionType, float, str]]:
        confusion_signals = ["不懂", "不理解", "为什么", "怎么回事", "搞不懂", "什么意思", "困惑"]
        practice_signals = ["代码", "编程", "写一个", "实现", "练习", "运行"]
        if any(s in text for s in confusion_signals):
            dialogue_type = "confusion"
            emotion = (EmotionType.CONFUSED, 0.7, "检测到困惑信号")
        elif any(s in text for s in practice_signals):
            dialogue_type = "practice"
            emotion = (EmotionType.CURIOUS, 0.6, "检测到实践意图")
        else:
            dialogue_type = "question"
            emotion = (EmotionType.NEUTRAL, 0.4, "常规提问")

        keywords = [w for w in text.split() if len(w) > 1][:5]
        profile_update = {
            "interaction_count": profile.interaction_count + 1,
            "cognitive_level": profile.cognitive_level.value if isinstance(profile.cognitive_level, DifficultyLevel) else profile.cognitive_level,
        }
        return profile_update, dialogue_type, keywords, emotion

    def _merge_profile(self, current: LearningProfile, update: dict[str, Any]) -> LearningProfile:
        data = current.model_dump()
        for k, v in update.items():
            if k in data:
                data[k] = v
        return LearningProfile.model_validate(data)


class PlannerAgent(BaseAgent):
    name = "planner"
    role = "路径规划智能体"
    description = "根据画像动态规划学习路径，确定下一步学习内容和难度"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            planner_output = await self._plan(state)
            state.add_message(DialogueRole.PLANNER, f"路径规划完成 | 目标: {planner_output.learning_objective}")
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                f"画像认知水平: {state.profile.cognitive_level}",
                f"目标: {planner_output.learning_objective}, 难度: {planner_output.difficulty_level}, 内容类型: {planner_output.content_types}",
                elapsed
            ))
            state.metadata["planner_output"] = planner_output.model_dump(mode="json")
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("路径规划", "", elapsed, "error", str(e)))
        return state

    async def _plan(self, state: StudentState) -> PlannerOutput:
        cognitive = state.profile.cognitive_level
        if isinstance(cognitive, DifficultyLevel):
            diff = cognitive
        else:
            diff = DifficultyLevel(cognitive) if cognitive in [e.value for e in DifficultyLevel] else DifficultyLevel.BASIC

        content_types = [ContentType.TEXT]
        style = state.profile.learning_style
        if isinstance(style, CognitiveStyle):
            pass
        else:
            style = CognitiveStyle(style) if style in [e.value for e in CognitiveStyle] else CognitiveStyle.PRAGMATIC

        if style == CognitiveStyle.VISUAL:
            content_types.append(ContentType.MINDMAP)
            content_types.append(ContentType.MERMAID)
        elif style == CognitiveStyle.PRAGMATIC:
            content_types.append(ContentType.CODE)
            content_types.append(ContentType.EXERCISE)

        recent = state.get_recent_messages(3)
        topic = "大数据技术基础"
        if recent:
            last = recent[-1].content.lower()
            if "hdfs" in last:
                topic = "HDFS分布式文件系统"
            elif "mapreduce" in last:
                topic = "MapReduce编程模型"
            elif "spark" in last:
                topic = "Spark内存计算"
            elif "flink" in last:
                topic = "Flink流处理"
            elif "排序" in last:
                topic = "排序算法"

        next_node = PathNode(
            course_id=state.course_id,
            chapter_id="ch_dynamic",
            knowledge_point_id="kp_dynamic",
            topic=topic,
            status="current",
            difficulty=diff,
        )

        return PlannerOutput(
            learning_objective=f"掌握{topic}的核心概念与应用",
            difficulty_level=diff,
            content_types=content_types,
            next_path_node=next_node,
            reasoning=f"基于认知水平({diff.value})和学习风格({style.value})动态规划",
        )


from state import CognitiveStyle


class DocumentGeneratorAgent(BaseAgent):
    name = "document_generator"
    role = "文档生成智能体"
    description = "生成结构化的知识文档和教材内容"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            output = await self._generate(state)
            state.metadata["document_output"] = output.model_dump(mode="json")
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "生成知识文档", f"文档长度: {len(output.text_content)}字", elapsed
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("文档生成", "", elapsed, "error", str(e)))
        return state

    async def _generate(self, state: StudentState) -> GeneratorOutput:
        user_input = state.get_recent_messages(1)
        text = user_input[0].content if user_input else ""
        mock_content = f"关于「{text[:20]}」的知识文档\n\n## 核心概念\n\n这是由文档生成智能体创建的结构化内容。\n\n## 要点总结\n\n1. 关键概念解析\n2. 应用场景分析\n3. 常见误区提醒"
        return GeneratorOutput(
            text_content=mock_content,
            content_type=ContentType.DOCUMENT,
            resources=[ResourceLink(url="https://ebook.hep.com.cn", title="参考教材", resource_type=ContentType.DOCUMENT)],
        )


class MindmapGeneratorAgent(BaseAgent):
    name = "mindmap_generator"
    role = "思维导图生成智能体"
    description = "生成Mermaid格式的思维导图和流程图"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            output = await self._generate(state)
            state.metadata["mindmap_output"] = output.model_dump(mode="json")
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "生成思维导图", f"导图节点数: 估算5-8个", elapsed
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("思维导图生成", "", elapsed, "error", str(e)))
        return state

    async def _generate(self, state: StudentState) -> GeneratorOutput:
        user_input = state.get_recent_messages(1)
        text = user_input[0].content if user_input else ""
        mermaid = f"```mermaid\ngraph TD\n    A[核心概念] --> B[子概念1]\n    A --> C[子概念2]\n    A --> D[子概念3]\n    B --> E[细节1]\n    B --> F[细节2]\n```"
        return GeneratorOutput(
            text_content=mermaid,
            content_type=ContentType.MERMAID,
        )


class ExerciseGeneratorAgent(BaseAgent):
    name = "exercise_generator"
    role = "习题生成智能体"
    description = "根据学习进度生成编程练习题和测验"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            output = await self._generate(state)
            state.metadata["exercise_output"] = output.model_dump(mode="json")
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "生成练习题", f"题目类型: 编程实践", elapsed
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("习题生成", "", elapsed, "error", str(e)))
        return state

    async def _generate(self, state: StudentState) -> GeneratorOutput:
        diff = state.profile.cognitive_level
        diff_str = diff.value if isinstance(diff, DifficultyLevel) else str(diff)
        mock_exercise = f"📝 题目：大数据处理实践\n\n题目描述：请实现一个MapReduce程序，完成以下任务...\n\n难度级别：{diff_str}\n\n输入格式：第一行包含整数n...\n输出格式：一行结果..."
        return GeneratorOutput(
            text_content=mock_exercise,
            content_type=ContentType.EXERCISE,
        )


class VideoContentAgent(BaseAgent):
    name = "video_content"
    role = "视频内容智能体"
    description = "推荐和推送相关的视频学习资源"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            output = await self._generate(state)
            state.metadata["video_output"] = output.model_dump(mode="json")
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "推送视频资源", f"推荐视频数: {len(output.resources)}", elapsed
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("视频推送", "", elapsed, "error", str(e)))
        return state

    async def _generate(self, state: StudentState) -> GeneratorOutput:
        return GeneratorOutput(
            text_content="📹 推荐学习视频",
            content_type=ContentType.VIDEO,
            resources=[
                ResourceLink(url="https://www.zhishikoo.com", title="知识点视频讲解", resource_type=ContentType.VIDEO, description="5分钟核心概念动画"),
                ResourceLink(url="https://ebook.hep.com.cn", title="教材配套视频", resource_type=ContentType.VIDEO, description="章节配套教学视频"),
            ],
        )


class ResourcePushAgent(BaseAgent):
    name = "resource_push"
    role = "资源推送智能体"
    description = "汇总所有生成智能体的输出，整合资源链接并推送"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            all_resources = []
            all_content_parts = []
            for key in ["document_output", "mindmap_output", "exercise_output", "video_output"]:
                data = state.metadata.get(key)
                if data and isinstance(data, dict):
                    output = GeneratorOutput.model_validate(data)
                    if output.text_content:
                        all_content_parts.append(output.text_content)
                    all_resources.extend(output.resources)

            state.metadata["final_resources"] = [r.model_dump(mode="json") for r in all_resources]
            state.metadata["final_content_parts"] = all_content_parts
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "汇总资源推送", f"资源数: {len(all_resources)}, 内容片段: {len(all_content_parts)}", elapsed
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("资源推送", "", elapsed, "error", str(e)))
        return state


class EvaluationAgent(BaseAgent):
    name = "evaluator"
    role = "评估智能体"
    description = "计算学习评估指标，更新学情画像"

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            interaction_count = state.profile.interaction_count
            socratic_pass_rate = state.profile.socratic_pass_rate
            if state.metadata.get("dialogue_type") == "confusion":
                socratic_pass_rate = min(1.0, socratic_pass_rate + 0.05)
            difficulty_map = {0: DifficultyLevel.BASIC, 1: DifficultyLevel.MEDIUM, 2: DifficultyLevel.ADVANCED}
            diff_idx = min(2, interaction_count // 10)
            difficulty_level = difficulty_map[diff_idx]

            state.profile.interaction_count = interaction_count
            state.profile.socratic_pass_rate = socratic_pass_rate
            state.profile.cognitive_level = difficulty_level

            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "评估学情",
                f"交互={interaction_count}, 启发率={socratic_pass_rate:.0%}, 难度={difficulty_level.value}",
                elapsed
            ))
            state.metadata["evaluation"] = {
                "interactionCount": interaction_count,
                "socraticPassRate": socratic_pass_rate,
                "difficultyLevel": difficulty_level.value,
                "codePracticeTime": state.profile.code_practice_time,
            }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("评估", "", elapsed, "error", str(e)))
        return state


class SocraticEvaluatorAgent(BaseAgent):
    name = "socratic_evaluator"
    role = "苏格拉底评估与辅导智能体"
    description = "通过苏格拉底式对话引导学生自主思考，评估学习效果，实现多轮启发式教学"

    MAX_WRONG_ROUNDS = 3
    PASS_RATE_INCREMENT = 0.33

    SOCRATIC_SYSTEM_PROMPT = """你是一位精通苏格拉底教学法的资深导师。你的核心教学原则如下：

【教育心理学引导策略】
1. 产婆术原则：绝不直接告知答案，通过层层递进的提问引导学生自己发现真理。
2. 最近发展区理论：问题难度始终略高于学生当前认知水平，保持适度挑战感。
3. 元认知唤醒：引导学生反思自己的思维过程，而非仅关注答案本身。
4. 正向强化：当学生回答方向正确时，立即给予具体、真诚的肯定。

【问题生成框架】
- 第一层：概念关联题 — "你注意到X和Y之间有什么联系吗？"
- 第二层：原理探究题 — "如果改变条件Z，结果会怎样？为什么？"
- 第三层：迁移应用题 — "你能把这个原理应用到场景W中吗？"

【反馈机制】
- 正确方向：肯定 → 指出具体亮点 → 抛出下一层递进问题
- 错误方向：不否定 → 引导反思 → 提供思考线索 → 重新提问
- 连续错误：逐步降低问题抽象度，提供更具体的思考锚点

【绝对禁止】
- 禁止输出教材原文内容
- 禁止直接给出答案
- 禁止使用"答案是..."、"正确做法是..."等直接告知句式
- 禁止在学生困惑时直接展示完整解释

你当前的教学上下文：
课程：{course_id}
主题：{topic}
学生认知水平：{cognitive_level}
对话轮次：{round_number}
历史正确次数：{correct_count}
历史错误次数：{wrong_count}

请根据以上信息，生成一个精准的苏格拉底式引导问题或反馈。"""

    JUDGE_SYSTEM_PROMPT = """你是一个精确的学生回答判别器。你的任务是根据问题和参考知识点，判断学生的回答方向是否正确。

【判断标准】
- 方向正确：学生理解了核心概念，即使表述不完美或缺少细节
- 方向错误：学生对核心概念存在根本性误解，或回答与问题无关

【输出格式】
只输出一个JSON对象：
{"correct": true/false, "reason": "简短说明判断依据"}

【注意】
- 宽容判断：只要学生展现出对核心概念的理解，即使不完整也应判定为正确
- 严格禁止输出任何解释性文字，只输出JSON"""

    FALLBACK_TEMPLATE = """看起来我们在这个问题上遇到了一些困难，让我换一种方式来帮你理解。

## 📖 {topic} — 图文详解

### 核心概念

{core_concept}

### 工作原理图解

```mermaid
{mermaid_diagram}
```

### 关键要点

{key_points}

### 记忆口诀

{mnemonic}

---

💡 **理解了这些基础之后，你可以试着用自己的话复述一下这个概念吗？**"""

    def __init__(self) -> None:
        super().__init__()
        self._socratic_state: dict[str, dict[str, Any]] = {}

    def _get_socratic_state(self, state: StudentState) -> dict[str, Any]:
        key = f"{state.student_id}_{state.context_id}"
        if key not in self._socratic_state:
            self._socratic_state[key] = {
                "round_number": 0,
                "correct_count": 0,
                "wrong_count": 0,
                "current_topic": "",
                "questions_asked": [],
                "last_judge_result": None,
                "fallback_triggered": False,
            }
        return self._socratic_state[key]

    def _reset_socratic_state(self, state: StudentState) -> None:
        key = f"{state.student_id}_{state.context_id}"
        self._socratic_state[key] = {
            "round_number": 0,
            "correct_count": 0,
            "wrong_count": 0,
            "current_topic": "",
            "questions_asked": [],
            "last_judge_result": None,
            "fallback_triggered": False,
        }

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            dialogue_type = state.metadata.get("dialogue_type", "question")
            socratic_data = self._get_socratic_state(state)

            if dialogue_type != "confusion" and not socratic_data.get("questions_asked"):
                await self._run_evaluation_only(state)
                return state

            socratic_data["round_number"] += 1
            topic = self._extract_topic(state)
            socratic_data["current_topic"] = topic

            user_input = ""
            recent = state.get_recent_messages(1)
            if recent:
                user_input = recent[0].content

            if socratic_data["round_number"] == 1:
                response_text = await self._generate_first_question(state, topic, socratic_data)
            else:
                is_correct = await self._judge_answer(state, user_input, topic, socratic_data)
                socratic_data["last_judge_result"] = is_correct

                if is_correct:
                    socratic_data["correct_count"] += 1
                    state.profile.socratic_pass_rate = min(
                        1.0,
                        state.profile.socratic_pass_rate + self.PASS_RATE_INCREMENT,
                    )
                    state.profile.interaction_count += 1

                    if socratic_data["correct_count"] >= 3 or state.profile.socratic_pass_rate >= 0.99:
                        response_text = await self._generate_completion_feedback(state, topic, socratic_data)
                        self._reset_socratic_state(state)
                    else:
                        response_text = await self._generate_next_question(state, topic, socratic_data)
                else:
                    socratic_data["wrong_count"] += 1
                    state.profile.interaction_count += 1

                    if socratic_data["wrong_count"] >= self.MAX_WRONG_ROUNDS:
                        response_text = await self._trigger_fallback(state, topic, socratic_data)
                        socratic_data["fallback_triggered"] = True
                        self._reset_socratic_state(state)
                    else:
                        response_text = await self._generate_hint(state, topic, socratic_data)

            socratic_data["questions_asked"].append(response_text[:100])
            state.metadata["socratic_response"] = response_text
            state.metadata["socratic_state"] = socratic_data

            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                f"苏格拉底辅导 | 轮次={socratic_data['round_number']}, "
                f"正确={socratic_data['correct_count']}, 错误={socratic_data['wrong_count']}, "
                f"启发率={state.profile.socratic_pass_rate:.0%}",
                response_text[:100],
                elapsed
            ))

        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log("苏格拉底辅导", "", elapsed, "error", str(e)))
        return state

    async def _run_evaluation_only(self, state: StudentState) -> None:
        state.profile.interaction_count += 1
        difficulty_map = {0: DifficultyLevel.BASIC, 1: DifficultyLevel.MEDIUM, 2: DifficultyLevel.ADVANCED}
        diff_idx = min(2, state.profile.interaction_count // 10)
        state.profile.cognitive_level = difficulty_map[diff_idx]
        state.metadata["evaluation"] = {
            "interactionCount": state.profile.interaction_count,
            "socraticPassRate": state.profile.socratic_pass_rate,
            "difficultyLevel": state.profile.cognitive_level.value if isinstance(state.profile.cognitive_level, DifficultyLevel) else state.profile.cognitive_level,
            "codePracticeTime": state.profile.code_practice_time,
        }

    def _extract_topic(self, state: StudentState) -> str:
        recent = state.get_recent_messages(5)
        for msg in reversed(recent):
            text = msg.content.lower()
            topic_keywords = {
                "hdfs": "HDFS分布式文件系统",
                "mapreduce": "MapReduce编程模型",
                "spark": "Spark内存计算框架",
                "flink": "Flink流处理引擎",
                "排序": "排序算法",
                "nosql": "NoSQL数据库",
                "zookeeper": "ZooKeeper分布式协调",
                "hadoop": "Hadoop生态系统",
            }
            for kw, topic in topic_keywords.items():
                if kw in text:
                    return topic
        return state.current_path[0].topic if state.current_path else "大数据技术基础"

    async def _generate_first_question(self, state: StudentState, topic: str, socratic_data: dict) -> str:
        cognitive = state.profile.cognitive_level
        cognitive_str = cognitive.value if isinstance(cognitive, DifficultyLevel) else str(cognitive)
        prompt = self.SOCRATIC_SYSTEM_PROMPT.format(
            course_id=state.course_id,
            topic=topic,
            cognitive_level=cognitive_str,
            round_number=1,
            correct_count=0,
            wrong_count=0,
        )
        try:
            from llm_stream import call_llm_async
            response = await call_llm_async(prompt, f"学生对{topic}感到困惑，请生成第一个启发式问题。", temperature=0.5)
            return response.strip()
        except Exception:
            return f"你注意到{topic}的核心设计是为了解决什么问题吗？试着从'为什么需要它'的角度思考一下。"

    async def _judge_answer(self, state: StudentState, user_answer: str, topic: str, socratic_data: dict) -> bool:
        last_question = socratic_data["questions_asked"][-1] if socratic_data["questions_asked"] else ""
        user_prompt = f"""参考知识点：{topic}
上一个问题：{last_question}
学生回答：{user_answer}

请判断学生的回答方向是否正确。"""

        for attempt in range(3):
            try:
                from llm_stream import call_llm_async
                result = await call_llm_async(
                    self.JUDGE_SYSTEM_PROMPT,
                    user_prompt,
                    temperature=0.1,
                )
                result = result.strip()
                if result.startswith("```"):
                    result = re.sub(r"^```(?:json)?\s*", "", result)
                    result = re.sub(r"\s*```$", "", result)
                judge_data = json.loads(result)
                return bool(judge_data.get("correct", False))
            except json.JSONDecodeError:
                if "true" in result.lower():
                    return True
                if "false" in result.lower():
                    return False
                continue
            except Exception:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue

        return len(user_answer) > 10

    async def _generate_next_question(self, state: StudentState, topic: str, socratic_data: dict) -> str:
        cognitive = state.profile.cognitive_level
        cognitive_str = cognitive.value if isinstance(cognitive, DifficultyLevel) else str(cognitive)
        prompt = self.SOCRATIC_SYSTEM_PROMPT.format(
            course_id=state.course_id,
            topic=topic,
            cognitive_level=cognitive_str,
            round_number=socratic_data["round_number"],
            correct_count=socratic_data["correct_count"],
            wrong_count=socratic_data["wrong_count"],
        )
        try:
            from llm_stream import call_llm_async
            response = await call_llm_async(
                prompt,
                f"学生回答正确，请给予肯定并抛出第{socratic_data['round_number'] + 1}个递进式问题。当前主题：{topic}",
                temperature=0.5,
            )
            return response.strip()
        except Exception:
            layer_questions = [
                f"很好！那你能进一步解释{topic}中的核心机制是如何工作的吗？",
                f"非常棒！现在试着思考：如果改变{topic}的某个关键参数，会产生什么影响？",
                f"太好了！最后一个问题：你能把{topic}的原理应用到一个实际场景中吗？",
            ]
            idx = min(socratic_data["correct_count"] - 1, len(layer_questions) - 1)
            return layer_questions[max(0, idx)]

    async def _generate_hint(self, state: StudentState, topic: str, socratic_data: dict) -> str:
        cognitive = state.profile.cognitive_level
        cognitive_str = cognitive.value if isinstance(cognitive, DifficultyLevel) else str(cognitive)
        prompt = self.SOCRATIC_SYSTEM_PROMPT.format(
            course_id=state.course_id,
            topic=topic,
            cognitive_level=cognitive_str,
            round_number=socratic_data["round_number"],
            correct_count=socratic_data["correct_count"],
            wrong_count=socratic_data["wrong_count"],
        )
        try:
            from llm_stream import call_llm_async
            response = await call_llm_async(
                prompt,
                f"学生回答方向不对，请给予引导性提示（不直接告知答案），帮助其找到正确方向。当前主题：{topic}，已错{socratic_data['wrong_count']}次",
                temperature=0.5,
            )
            return response.strip()
        except Exception:
            hints = [
                f"让我们换个角度思考：{topic}最核心的目标是什么？从这个目标出发，你能想到什么？",
                f"提示：试着回忆一下{topic}的设计初衷。它要解决的根本问题是什么？",
                f"再想想：{topic}中的关键组件各自承担什么角色？它们之间如何协作？",
            ]
            idx = min(socratic_data["wrong_count"] - 1, len(hints) - 1)
            return hints[max(0, idx)]

    async def _generate_completion_feedback(self, state: StudentState, topic: str, socratic_data: dict) -> str:
        try:
            from llm_stream import call_llm_async
            response = await call_llm_async(
                "你是一位鼓励型导师。学生已通过苏格拉底式对话成功理解了知识点，请给予温暖的肯定和总结。",
                f"学生通过{socratic_data['correct_count']}轮正确回答，成功理解了{topic}。请给出完成反馈。",
                temperature=0.6,
            )
            return response.strip()
        except Exception:
            return f"🎉 太棒了！你通过自主思考成功理解了{topic}的核心概念！这种主动探索的学习方式非常有效，继续保持！"

    async def _trigger_fallback(self, state: StudentState, topic: str, socratic_data: dict) -> str:
        topic_data = self._get_topic_fallback_data(topic)
        content = self.FALLBACK_TEMPLATE.format(
            topic=topic,
            core_concept=topic_data["core_concept"],
            mermaid_diagram=topic_data["mermaid"],
            key_points=topic_data["key_points"],
            mnemonic=topic_data["mnemonic"],
        )
        state.profile.socratic_pass_rate = min(1.0, state.profile.socratic_pass_rate + 0.1)
        return content

    def _get_topic_fallback_data(self, topic: str) -> dict[str, str]:
        fallback_db: dict[str, dict[str, str]] = {
            "HDFS分布式文件系统": {
                "core_concept": "HDFS采用Master/Slave架构，NameNode管理元数据（命名空间、数据块映射），DataNode存储实际数据块。默认3副本保证可靠性。",
                "mermaid": "graph TD\n    A[Client] --> B[NameNode]\n    B --> C[DataNode 1]\n    B --> D[DataNode 2]\n    B --> E[DataNode 3]\n    C --> F[数据块1 副本]\n    D --> F2[数据块1 副本]\n    E --> F3[数据块1 副本]",
                "key_points": "1. NameNode：元数据管家，不存实际数据\n2. DataNode：数据存储工人，定期心跳汇报\n3. 3副本策略：同机架1份 + 跨机架2份\n4. 写入Pipeline：Client→DN1→DN2→DN3",
                "mnemonic": "📝 记：Name管名不管数，Data存数不存名，三副本保平安，Pipeline串着传",
            },
            "MapReduce编程模型": {
                "core_concept": "MapReduce将计算分为Map（数据切分与局部处理）和Reduce（汇总聚合）两个阶段，核心思想是分而治之和数据本地化计算。",
                "mermaid": "graph LR\n    A[输入数据] --> B[Map阶段]\n    B --> C[Shuffle排序]\n    C --> D[Reduce阶段]\n    D --> E[输出结果]",
                "key_points": "1. Map阶段：输入分片→并行处理→输出<key,value>\n2. Shuffle：按Key排序分组传输\n3. Reduce：同一Key的Value聚合\n4. 核心思想：移动计算而非移动数据",
                "mnemonic": "📝 记：Map分而治之，Shuffle按Key聚，Reduce合而为一，数据不动计算动",
            },
            "Spark内存计算框架": {
                "core_concept": "Spark基于RDD（弹性分布式数据集）实现内存计算，通过Lineage血统机制实现容错，迭代计算性能比MapReduce提升10-100倍。",
                "mermaid": "graph TD\n    A[RDD] --> B[Transformation]\n    B --> C[RDD]\n    C --> D[Action]\n    D --> E[结果]\n    A -.->|Lineage| F[容错重建]",
                "key_points": "1. RDD特性：不可变、分区、容错(Lineage)\n2. Transformation：懒执行，构建DAG\n3. Action：触发实际计算\n4. 内存缓存：减少磁盘IO",
                "mnemonic": "📝 记：RDD不可变但能溯源，Transform懒执行Action催，内存缓存加速跑，Lineage保你不迷路",
            },
        }
        return fallback_db.get(topic, {
            "core_concept": f"{topic}是大数据技术体系中的重要组成部分，理解其核心原理对掌握整个技术栈至关重要。",
            "mermaid": f"graph TD\n    A[{topic}] --> B[核心概念1]\n    A --> C[核心概念2]\n    A --> D[核心概念3]",
            "key_points": f"1. {topic}的设计目标和核心价值\n2. 关键组件及其协作方式\n3. 典型应用场景和最佳实践",
            "mnemonic": f"📝 记：{topic}三要素 — 目标、组件、场景",
        })


class MasterController:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._pipeline: list[BaseAgent] = []
        self._generator_agents: dict[str, BaseAgent] = {}
        self._pre_pipeline: list[BaseAgent] = []
        self._logger = logging.getLogger("starlearn.master_controller")

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def register_generator(self, name: str, agent: BaseAgent) -> None:
        self._generator_agents[name] = agent
        self._agents[agent.name] = agent

    def set_pipeline(self, pipeline: list[BaseAgent]) -> None:
        self._pipeline = pipeline

    def set_pre_pipeline(self, agents: list[BaseAgent]) -> None:
        self._pre_pipeline = agents

    def on_login(self, state: StudentState) -> None:
        self._logger.info(f"Login event triggered for student={state.student_id}")
        if "echo" not in self._agents:
            self.register_agent(EchoAgent())
        if self._agents.get("echo") not in self._pre_pipeline:
            self._pre_pipeline.insert(0, self._agents["echo"])
            self._logger.info("EchoAgent added to pre-pipeline for login event")

    def route_generators(self, state: StudentState) -> list[BaseAgent]:
        planner_data = state.metadata.get("planner_output", {})
        if isinstance(planner_data, dict):
            planner = PlannerOutput.model_validate(planner_data) if planner_data else None
        else:
            planner = None

        if not planner:
            return [self._generator_agents.get("document_generator", DocumentGeneratorAgent())]

        selected: list[BaseAgent] = []
        content_types = planner.content_types
        type_to_agent: dict[ContentType, str] = {
            ContentType.TEXT: "document_generator",
            ContentType.DOCUMENT: "document_generator",
            ContentType.MERMAID: "mindmap_generator",
            ContentType.MINDMAP: "mindmap_generator",
            ContentType.EXERCISE: "exercise_generator",
            ContentType.CODE: "exercise_generator",
            ContentType.VIDEO: "video_content",
        }

        for ct in content_types:
            agent_name = type_to_agent.get(ct)
            if agent_name and agent_name in self._generator_agents:
                agent = self._generator_agents[agent_name]
                if agent not in selected:
                    selected.append(agent)

        dialogue_type = state.metadata.get("dialogue_type", "question")
        if dialogue_type == "confusion":
            doc_agent = self._generator_agents.get("document_generator")
            if doc_agent and doc_agent not in selected:
                selected.insert(0, doc_agent)

        if not selected:
            selected.append(self._generator_agents.get("document_generator", DocumentGeneratorAgent()))

        return selected

    async def execute(
        self,
        state: StudentState,
        on_step_complete: Callable[[AgentStepLog], Awaitable[None]] | None = None,
    ) -> StudentState:
        last_log_idx = len(state.workflow_logs)

        for agent in self._pre_pipeline:
            self._logger.info(f"Pre-pipeline: running {agent.name}")
            state = await agent.run(state)
            if on_step_complete:
                for log in state.workflow_logs[last_log_idx:]:
                    try:
                        await on_step_complete(log)
                    except Exception:
                        pass
                last_log_idx = len(state.workflow_logs)

        for agent in self._pipeline:
            state = await agent.run(state)
            if on_step_complete:
                for log in state.workflow_logs[last_log_idx:]:
                    try:
                        await on_step_complete(log)
                    except Exception:
                        pass
                last_log_idx = len(state.workflow_logs)

        generators = self.route_generators(state)
        for gen in generators:
            state = await gen.run(state)
            if on_step_complete:
                for log in state.workflow_logs[last_log_idx:]:
                    try:
                        await on_step_complete(log)
                    except Exception:
                        pass
                last_log_idx = len(state.workflow_logs)

        if "resource_push" in self._agents:
            state = await self._agents["resource_push"].run(state)
            if on_step_complete:
                for log in state.workflow_logs[last_log_idx:]:
                    try:
                        await on_step_complete(log)
                    except Exception:
                        pass
                last_log_idx = len(state.workflow_logs)

        if "evaluator" in self._agents:
            state = await self._agents["evaluator"].run(state)
            if on_step_complete:
                for log in state.workflow_logs[last_log_idx:]:
                    try:
                        await on_step_complete(log)
                    except Exception:
                        pass
                last_log_idx = len(state.workflow_logs)

        return state


class EchoAgent(BaseAgent):
    name = "echo"
    role = "记忆回响智能体"
    description = "检测遗忘节点并生成复习微挑战"

    FORGET_THRESHOLD_DAYS = 3

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            stale_nodes = self._detect_stale_nodes(state)
            if not stale_nodes:
                elapsed = int((time.time() - start) * 1000)
                state.add_workflow_log(self._create_log(
                    "记忆回响扫描", "所有节点均在复习周期内，无需干预", elapsed
                ))
                return state

            challenges = self._generate_challenges(stale_nodes)
            echo_message = self._format_echo_message(stale_nodes, challenges)

            state.metadata["echo_intervention"] = {
                "stale_nodes": [n.model_dump(mode="json") if hasattr(n, "model_dump") else n for n in stale_nodes],
                "challenges": challenges,
                "message": echo_message,
            }

            state.add_message(
                DialogueRole.SYSTEM,
                echo_message,
                metadata={"source": "echo_agent", "type": "review_intervention"},
            )

            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "记忆回响触发",
                f"检测到 {len(stale_nodes)} 个遗忘风险节点，已生成复习微挑战",
                elapsed,
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "记忆回响", "", elapsed, "error", str(e)
            ))
        return state

    def _detect_stale_nodes(self, state: StudentState) -> list:
        stale = []
        now = datetime.now()
        threshold = timedelta(days=self.FORGET_THRESHOLD_DAYS)

        for node in state.current_path:
            if not hasattr(node, "status") or node.status != "completed":
                continue
            last_reviewed = None
            if hasattr(node, "metadata") and isinstance(node.metadata, dict):
                ts = node.metadata.get("last_reviewed_at") or node.metadata.get("completed_at")
                if ts:
                    if isinstance(ts, datetime):
                        last_reviewed = ts
                    elif isinstance(ts, str):
                        try:
                            last_reviewed = datetime.fromisoformat(ts)
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(ts, (int, float)):
                        last_reviewed = datetime.fromtimestamp(ts)

            if last_reviewed and (now - last_reviewed) > threshold:
                stale.append(node)

        return stale

    def _generate_challenges(self, stale_nodes: list) -> list[dict[str, str]]:
        challenges = []
        for node in stale_nodes:
            topic = getattr(node, "topic", None) or getattr(node, "name", None) or getattr(node, "title", None) or "未知节点"
            key_concept = topic.split("：")[-1] if "：" in topic else topic
            challenge = {
                "topic": topic,
                "type": "fill_blank",
                "question": f"在{topic}中，核心概念______是理解该知识点的关键，请填写完整。",
                "hint": f"提示：回忆{key_concept}的定义和核心特征",
                "answer": key_concept,
            }
            challenges.append(challenge)
        return challenges

    def _format_echo_message(self, stale_nodes: list, challenges: list[dict[str, str]]) -> str:
        lines = ["🔔 **记忆回响提醒**", ""]
        lines.append(f"检测到 {len(stale_nodes)} 个知识点已超过 {self.FORGET_THRESHOLD_DAYS} 天未复习，遗忘风险较高：")
        lines.append("")

        for i, ch in enumerate(challenges, 1):
            lines.append(f"**{i}. {ch['topic']}**")
            lines.append(f"   📝 微挑战：{ch['question']}")
            lines.append(f"   💡 {ch['hint']}")
            lines.append("")

        lines.append("建议花几分钟完成这些微挑战，巩固记忆效果！")
        return "\n".join(lines)


class FlashcardAgent(BaseAgent):
    name = "flashcard"
    role = "知识胶囊智能体"
    description = "将章节知识压缩为记忆闪卡，辅助高效复习"

    SYSTEM_PROMPT = """你是一位精通认知科学和间隔重复法的知识压缩专家。你的任务是将学习内容压缩为高质量的记忆闪卡(Flashcards)。

## 角色定义
你是一名经验丰富的教育心理学家，擅长将复杂知识提炼为简洁、精准的记忆锚点。

## 压缩规则
1. 每张闪卡正面必须是明确的提问或填空，不能是模糊的描述
2. 背面答案必须精炼，不超过200字，只保留核心概念和关键逻辑
3. 提示(hint)必须指出该知识点最常见的误解或易错点，不超过50字
4. 【强制要求】每个章节必须生成至少10张闪卡，确保覆盖该章节的所有重要知识点
5. 闪卡之间应有递进关系：基础概念→核心原理→应用场景→易错辨析→综合运用
6. 避免纯记忆型题目，优先考察理解和推理能力
7. 题目类型应多样化：概念辨析、原理推导、场景应用、对比分析、判断正误等
8. 如果内容较少不足以生成10题，请从不同角度深入挖掘，如：定义、原理、对比、应用、限制、演进等

## 输出格式
严格输出以下JSON格式，不要添加任何其他文字：
```json
{
  "flashcards": [
    {
      "front": "简洁明确的问题",
      "back": "核心概念答案(≤200字)",
      "hint": "易错点提示(≤50字)"
    }
  ]
}
```

## 数量要求（最高优先级）
- 必须生成至少10张闪卡，这是硬性要求
- 理想数量为10-15张，内容丰富时可达20张
- 绝对不允许生成少于10张闪卡
- 如果内容确实有限，请从多维度拆解知识点以满足最低数量要求

## 质量控制标准
- 正面问题必须能独立理解，不需要额外上下文
- 背面答案必须完整回答正面问题，不能含糊
- 提示必须具有实际指导价值，不能是空洞的"注意细节"
- 优先覆盖高频考点和核心概念
- 10张闪卡应覆盖该章节至少80%的核心知识点"""

    MIN_FLASHCARD_COUNT = 10
    MAX_RETRY_ATTEMPTS = 2

    async def run(self, state: StudentState, **kwargs: Any) -> StudentState:
        start = time.time()
        try:
            chapter_content = kwargs.get("chapter_content", "")
            chapter_name = kwargs.get("chapter_name", "")
            course_id = state.course_id

            if not chapter_content and state.dialogue_history:
                chapter_content = self._extract_chapter_from_history(state)
            if not chapter_name:
                chapter_name = state.metadata.get("current_chapter", "当前章节")

            if not chapter_content or len(chapter_content.strip()) < 50:
                elapsed = int((time.time() - start) * 1000)
                state.add_workflow_log(self._create_log(
                    "知识胶囊生成", "内容不足50字，跳过闪卡生成", elapsed
                ))
                state.metadata["flashcards"] = {
                    "flashcards": [],
                    "message": "内容过少，无法生成有效闪卡，请继续学习后再试。"
                }
                return state

            flashcards = await self._generate_flashcards(chapter_content, chapter_name, course_id)
            card_count = len(flashcards.get("flashcards", []))

            retry_count = 0
            while card_count < self.MIN_FLASHCARD_COUNT and retry_count < self.MAX_RETRY_ATTEMPTS:
                retry_count += 1
                logging.warning(f"[FlashcardAgent] Only {card_count} cards generated (min {self.MIN_FLASHCARD_COUNT}), retry {retry_count}/{self.MAX_RETRY_ATTEMPTS}")
                retry_result = await self._generate_flashcards(chapter_content, chapter_name, course_id)
                retry_cards = retry_result.get("flashcards", [])
                if len(retry_cards) > card_count:
                    flashcards = retry_result
                    card_count = len(retry_cards)
                if card_count >= self.MIN_FLASHCARD_COUNT:
                    break

            if card_count < self.MIN_FLASHCARD_COUNT and card_count > 0:
                existing = flashcards.get("flashcards", [])
                expanded = self._expand_flashcards(existing, chapter_name, self.MIN_FLASHCARD_COUNT - card_count)
                flashcards = {"flashcards": expanded}
                card_count = len(expanded)

            state.metadata["flashcards"] = flashcards
            state.add_message(
                DialogueRole.SYSTEM,
                f"已为「{chapter_name}」生成 {len(flashcards.get('flashcards', []))} 张知识胶囊",
                metadata={"source": "flashcard_agent", "type": "flashcard_generation"},
            )

            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "知识胶囊生成",
                f"为「{chapter_name}」生成 {len(flashcards.get('flashcards', []))} 张闪卡",
                elapsed,
            ))
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            state.add_workflow_log(self._create_log(
                "知识胶囊生成", "", elapsed, "error", str(e)
            ))
            state.metadata["flashcards"] = {
                "flashcards": [],
                "message": f"闪卡生成失败：{str(e)}"
            }
        return state

    def _extract_chapter_from_history(self, state: StudentState) -> str:
        parts = []
        for msg in state.dialogue_history[-10:]:
            if msg.role == DialogueRole.STUDENT and msg.content:
                parts.append(msg.content)
            elif msg.role in (DialogueRole.SYSTEM, DialogueRole.PROFILER, DialogueRole.PLANNER, DialogueRole.GENERATOR) and msg.content:
                parts.append(msg.content[:500])
        return "\n".join(parts)

    def _expand_flashcards(self, existing: list, chapter_name: str, needed: int) -> list:
        dimensions = [
            ("定义与概念", "请给出{topic}的精确定义，并说明其核心内涵"),
            ("核心原理", "{topic}的底层工作原理是什么？请简述其机制"),
            ("对比辨析", "{topic}与相关概念有何本质区别？请对比说明"),
            ("应用场景", "{topic}在实际中有哪些典型应用？请举例说明"),
            ("限制与边界", "{topic}的适用范围和局限性是什么？"),
            ("演进与发展", "{topic}是如何发展演进的？其未来趋势如何"),
            ("常见误区", "关于{topic}最常见的误解是什么？正确理解是什么"),
            ("关键特征", "{topic}有哪些关键特征或属性？请列举说明"),
        ]
        expanded = list(existing)
        dim_idx = 0
        for card in existing:
            used_dims = [d[0] for d in dimensions if d[0] in card.get("front", "")]
            if used_dims:
                dim_idx = max(dim_idx, next((i for i, d in enumerate(dimensions) if d[0] in used_dims[0]), 0) + 1)

        for i in range(needed):
            dim = dimensions[dim_idx % len(dimensions)]
            front = f"【{dim[0]}】{dim[1].format(topic=chapter_name)}"
            back = f"请通过深入学习「{chapter_name}」来获取{dim[0]}方面的详细解答"
            hint = f"从{dim[0]}角度思考"
            expanded.append({"front": front, "back": back, "hint": hint})
            dim_idx += 1

        return expanded

    async def _generate_flashcards(self, content: str, chapter_name: str, course_id: str) -> dict:
        from llm_stream import call_llm_stream_with_log
        user_prompt = f"""课程：{course_id}
章节：{chapter_name}

学习内容：
{content[:3000]}

请为以上内容生成记忆闪卡。重要提醒：必须生成至少10张闪卡，确保全面覆盖知识点。"""

        full_text = ""
        async for event in call_llm_stream_with_log(
            self.SYSTEM_PROMPT,
            user_prompt,
            agent_name=self.name,
            temperature=0.4,
        ):
            if event["type"] == "text":
                full_text += event["content"]
            elif event["type"] == "done":
                full_text = event.get("full_text", full_text)

        return self._parse_flashcard_response(full_text)

    def _parse_flashcard_response(self, response: str) -> dict:
        import json as _json
        json_str = response.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        data = None

        try:
            data = _json.loads(json_str)
        except _json.JSONDecodeError:
            pass

        if data is None:
            data = self._extract_json_truncated(response)

        if data is None:
            for i in range(len(json_str)):
                if json_str[i] == "{":
                    for j in range(len(json_str) - 1, -1, -1):
                        if json_str[j] == "}":
                            try:
                                data = _json.loads(json_str[i:j + 1])
                                break
                            except _json.JSONDecodeError:
                                continue
                    break
            else:
                return {"flashcards": [], "message": "无法解析闪卡数据，请重试"}

        if data is None:
            return {"flashcards": [], "message": "无法解析闪卡数据，请重试"}

        flashcards = data.get("flashcards", []) if isinstance(data, dict) else data if isinstance(data, list) else []

        validated = []
        for card in flashcards:
            if not isinstance(card, dict):
                continue
            front = str(card.get("front", "")).strip()
            back = str(card.get("back", "")).strip()
            hint = str(card.get("hint", "")).strip()
            if not front or not back:
                continue
            if len(back) > 200:
                back = back[:197] + "..."
            if len(hint) > 50:
                hint = hint[:47] + "..."
            validated.append({"front": front, "back": back, "hint": hint})

        return {"flashcards": validated}

    def _extract_json_truncated(self, text: str) -> dict | None:
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find('{')
        if start == -1:
            return None

        depth = 0
        last_valid_close = -1
        for i in range(start, len(cleaned)):
            if cleaned[i] == '{':
                depth += 1
            elif cleaned[i] == '}':
                depth -= 1
                if depth == 0:
                    last_valid_close = i
                    break

        if last_valid_close > 0:
            try:
                return json.loads(cleaned[start:last_valid_close + 1])
            except json.JSONDecodeError:
                pass

        if depth > 0:
            for close_pos in range(len(cleaned) - 1, start, -1):
                if cleaned[close_pos] == '}':
                    candidate = cleaned[start:close_pos + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue

            stacked = cleaned[start:]
            for _ in range(depth):
                stacked += '}'
            try:
                return json.loads(stacked)
            except json.JSONDecodeError:
                pass

            array_match = re.search(r'"flashcards"\s*:\s*\[', stacked)
            if array_match:
                arr_start = stacked.find('[', array_match.start())
                if arr_start != -1:
                    arr_content = stacked[arr_start:]
                    if not arr_content.rstrip().endswith(']'):
                        arr_content = arr_content.rstrip().rstrip(',')
                        if arr_content.endswith(','):
                            arr_content = arr_content[:-1]
                        arr_content += ']'
                    try:
                        parsed = json.loads(arr_content)
                        return {"flashcards": parsed} if isinstance(parsed, list) else parsed
                    except json.JSONDecodeError:
                        last_obj = 0
                        while True:
                            obj_start = arr_content.find('{', last_obj)
                            if obj_start == -1:
                                break
                            obj_end = arr_content.find('}', obj_start)
                            if obj_end == -1:
                                break
                            last_obj = obj_end + 1
                        if last_obj > 0:
                            fixed = arr_content[:last_obj] + ']'
                            try:
                                parsed = json.loads(fixed)
                                return {"flashcards": parsed} if isinstance(parsed, list) else parsed
                            except json.JSONDecodeError:
                                pass

        return None


def create_default_controller() -> MasterController:
    controller = MasterController()

    profiler = ProfilerAgent()
    planner = PlannerAgent()
    doc_gen = DocumentGeneratorAgent()
    mindmap_gen = MindmapGeneratorAgent()
    exercise_gen = ExerciseGeneratorAgent()
    video_gen = VideoContentAgent()
    resource_push = ResourcePushAgent()
    evaluator = EvaluationAgent()
    socratic_evaluator = SocraticEvaluatorAgent()
    echo = EchoAgent()
    flashcard = FlashcardAgent()

    controller.register_agent(profiler)
    controller.register_agent(planner)
    controller.register_agent(resource_push)
    controller.register_agent(evaluator)
    controller.register_agent(socratic_evaluator)
    controller.register_agent(echo)
    controller.register_agent(flashcard)

    controller.register_generator("document_generator", doc_gen)
    controller.register_generator("mindmap_generator", mindmap_gen)
    controller.register_generator("exercise_generator", exercise_gen)
    controller.register_generator("video_content", video_gen)
    controller.register_generator("socratic_evaluator", socratic_evaluator)

    controller.set_pipeline([profiler, planner])

    return controller
