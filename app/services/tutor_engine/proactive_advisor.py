# -*- coding: utf-8 -*-
"""
ProactiveAdvisor — 主动推送决策器

基于 RichContext 和 ResponseEnvelope 决策是否需要主动推送，
以及推送什么内容。包含 25+ 种触发场景。

设计原则：
  - 规则驱动：每种触发场景对应一条规则
  - 优先级分层：CRITICAL > HIGH > NORMAL > LOW
  - 与 ActionLedger 协同：避免重复暴露
  - 与 LinkRecommender 协同：推送可附带链接
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.services.tutor_engine.action_ledger import ActionLedger
from app.services.tutor_engine.models import (
    ActionType,
    Link,
    MessagePriority,
    ProactiveAction,
    ResponseEnvelope,
    RichContext,
    TutorEvent,
    TutorEventType,
)

logger = logging.getLogger("starlearn.tutor_engine")


class ProactiveAdvisor:
    """
    主动推送决策器。

    使用示例:
        advisor = ProactiveAdvisor()
        actions = await advisor.advise(event, rich_context, envelope, action_ledger)
    """

    def __init__(self):
        # 规则注册表：事件类型 -> 规则函数列表
        self._rules: dict[TutorEventType, list] = {
            TutorEventType.QUESTION_ASKED: [
                self._rule_practice_prompt,
                self._rule_health_reminder,
                self._rule_forced_break,
            ],
            TutorEventType.STRUGGLE_DETECTED: [
                self._rule_struggle_intervention,
            ],
            TutorEventType.LOGIN_GREETING: [
                self._rule_login_greeting,
            ],
            TutorEventType.REVIEW_DUE: [
                self._rule_review_reminder,
            ],
            TutorEventType.DEADLINE_APPROACHING: [
                self._rule_deadline_warning,
            ],
            TutorEventType.IDLE_TIMEOUT: [
                self._rule_idle_reminder,
            ],
            TutorEventType.CODE_NOT_WRITTEN: [
                self._rule_code_not_written,
            ],
            TutorEventType.CODE_NOT_RUN: [
                self._rule_code_not_run,
            ],
            TutorEventType.ERROR_IGNORED: [
                self._rule_error_ignored,
            ],
            TutorEventType.COPY_PASTE_DETECTED: [
                self._rule_copy_paste,
            ],
            TutorEventType.DEPRECATED_API_USED: [
                self._rule_deprecated_api,
            ],
            TutorEventType.TAB_SWITCHING: [
                self._rule_tab_switching,
            ],
            TutorEventType.CONSECUTIVE_WRONGS: [
                self._rule_consecutive_wrongs,
            ],
            TutorEventType.DAILY_PLAN_INCOMPLETE: [
                self._rule_daily_plan_incomplete,
            ],
            TutorEventType.PATH_DEVIATION: [
                self._rule_path_deviation,
            ],
            TutorEventType.PREREQUISITE_UNLOCKED: [
                self._rule_prerequisite_unlocked,
            ],
            TutorEventType.LEARNING_SLUMP: [
                self._rule_learning_slump,
            ],
            TutorEventType.PROGRESS_MILESTONE: [
                self._rule_milestone,
            ],
            TutorEventType.GOLDEN_HOUR: [
                self._rule_golden_hour,
            ],
            TutorEventType.FRAGMENT_TIME: [
                self._rule_fragment_time,
            ],
        }

    async def advise(
        self,
        event: TutorEvent,
        rich: RichContext,
        envelope: ResponseEnvelope,
        ledger: ActionLedger,
    ) -> list[ProactiveAction]:
        """
        决策主动推送。

        根据事件类型执行对应的规则，收集所有推送动作，
        按优先级排序后返回。
        """
        actions: list[ProactiveAction] = []
        student_id = event.student_id

        # 执行该事件类型对应的所有规则
        rules = self._rules.get(event.type, [])
        for rule in rules:
            try:
                result = rule(event, rich, envelope, ledger)
                if result:
                    if isinstance(result, list):
                        actions.extend(result)
                    else:
                        actions.append(result)
            except Exception as e:
                logger.warning(f"[ProactiveAdvisor] 规则 {rule.__name__} 失败: {e}")

        # 通用规则（不受事件类型限制，每次检查）
        actions.extend(self._check_universal_rules(event, rich, envelope, ledger))

        # 按优先级排序
        actions.sort(key=lambda a: a.priority.value)

        # 去重：同一 action_type 只保留一条
        seen_types = set()
        unique = []
        for a in actions:
            if a.action_type not in seen_types:
                seen_types.add(a.action_type)
                unique.append(a)

        return unique

    # ------------------------------------------------------------------
    # Critical 规则
    # ------------------------------------------------------------------

    def _rule_struggle_intervention(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """困难干预"""
        metrics = event.get_struggle_metrics()
        idle = metrics.get("idle_seconds", 0)
        errors = metrics.get("error_count", 0)

        if idle > 120:
            return ProactiveAction(
                action_type=ActionType.STRUGGLE_IDLE,
                priority=MessagePriority.CRITICAL,
                delay_seconds=0,
                title="需要帮忙吗？",
                content="我注意到你停留了一段时间，要不要换个角度思考？或者我帮你分解一下问题？",
                action_label="获取提示",
            )

        if errors > 3:
            return ProactiveAction(
                action_type=ActionType.STRUGGLE_ERROR,
                priority=MessagePriority.CRITICAL,
                delay_seconds=0,
                title="遇到困难了？",
                content="反复遇到这个问题很正常，让我用苏格拉底式提问引导你。",
                action_label="开始引导",
            )

        return None

    def _rule_error_ignored(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """报错后不查看"""
        if not ledger.recently_exposed(event.student_id, "error_ignored", minutes=10):
            return ProactiveAction(
                action_type=ActionType.ERROR_IGNORED,
                priority=MessagePriority.CRITICAL,
                delay_seconds=0,
                title="报错信息里有线索",
                content="运行出错了？报错信息通常包含关键线索。点击这里学习如何读懂报错。",
                action_label="学习读报错",
            )
        return None

    def _rule_consecutive_wrongs(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """连续答错"""
        count = event.payload.get("wrong_count", 0)
        if count >= 5 and not ledger.recently_exposed(event.student_id, "consecutive_wrongs", minutes=15):
            return ProactiveAction(
                action_type=ActionType.CONSECUTIVE_WRONGS,
                priority=MessagePriority.CRITICAL,
                delay_seconds=0,
                title="别灰心！",
                content=f"连续错了 {count} 题确实让人沮丧。每个人学编程都会卡壳，休息一下，或者我换种方式讲给你听？",
                action_label="换个方式讲",
            )
        return None

    # ------------------------------------------------------------------
    # High 规则
    # ------------------------------------------------------------------

    def _rule_practice_prompt(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """趁热打铁：问答后推荐练习"""
        question = event.get_question_text()
        if not question:
            return None

        # 从回答中提取核心知识点
        topic = rich.learning_state.last_study_topic or question[:20]

        if ledger.recently_exposed(event.student_id, topic, minutes=10):
            return None

        # 查找是否有相关练习链接
        practice_link = None
        for link in envelope.links:
            if link.source == "rag" and link.metadata.get("has_practice"):
                practice_link = link
                break

        return ProactiveAction(
            action_type=ActionType.PRACTICE_PROMPT,
            priority=MessagePriority.HIGH,
            delay_seconds=45,
            title="趁热打铁",
            content=f"刚学了「{topic}」，做个小练习巩固一下？",
            action_label="去做练习",
            attached_link=practice_link,
            metadata={"topic": topic},
        )

    def _rule_review_reminder(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> list[ProactiveAction]:
        """SM2 遗忘曲线复习提醒"""
        actions = []
        for item in rich.sm2_due_items[:2]:
            topic = f"sm2:{item.knowledge_point}"
            if ledger.recently_exposed(event.student_id, topic, minutes=30):
                continue

            link = Link(
                type="internal",
                title=f"复习：{item.knowledge_point}",
                url=f"/review.html?item={item.id}",
                description="根据你的记忆曲线，现在复习效果最好",
            )

            actions.append(ProactiveAction(
                action_type=ActionType.REVIEW_REMINDER,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="📚 该复习了",
                content=f"{item.knowledge_point} 到了最佳复习时间，花 2 分钟回顾一下吧？",
                action_label="开始复习",
                attached_link=link,
                metadata={"topic": topic},
            ))
        return actions

    def _rule_deadline_warning(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> list[ProactiveAction]:
        """课程截止日期预警"""
        actions = []
        for dl in rich.upcoming_deadlines:
            topic = f"deadline:{dl.task_id}"
            if ledger.recently_exposed(event.student_id, topic, hours=24):
                continue

            if dl.days_left <= 1:
                actions.append(ProactiveAction(
                    action_type=ActionType.DEADLINE_URGENT,
                    priority=MessagePriority.HIGH,
                    delay_seconds=0,
                    title="⏰ 明天截止",
                    content=f"「{dl.task_name}」明天就要截止了，记得提交哦！",
                    action_label="去提交",
                ))
            elif dl.days_left <= 3:
                actions.append(ProactiveAction(
                    action_type=ActionType.DEADLINE_WARNING,
                    priority=MessagePriority.NORMAL,
                    delay_seconds=0,
                    title=f"📅 {dl.days_left}天后截止",
                    content=f"「{dl.task_name}」还有 {dl.days_left} 天截止",
                    action_label="查看任务",
                ))
        return actions

    def _rule_forced_break(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """强制休息建议"""
        mins = rich.learning_state.today_minutes
        if mins > 150 and not ledger.recently_exposed(event.student_id, "forced_break", hours=3):
            return ProactiveAction(
                action_type=ActionType.FORCED_BREAK,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="⚠️ 该休息了",
                content="连续学习超过 2.5 小时了，建议休息 15 分钟，保护视力和注意力。休息后效率会更高！",
                action_label="知道了",
            )
        return None

    def _rule_code_not_written(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """只看不练提醒"""
        if not ledger.recently_exposed(event.student_id, "code_not_written", minutes=20):
            return ProactiveAction(
                action_type=ActionType.CODE_NOT_WRITTEN,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="动手写一写",
                content="看了这么久，动手写一写印象更深哦。编程是实践的艺术！",
                action_label="打开编辑器",
            )
        return None

    def _rule_code_not_run(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """写了但没运行"""
        if not ledger.recently_exposed(event.student_id, "code_not_run", minutes=10):
            return ProactiveAction(
                action_type=ActionType.CODE_NOT_RUN,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="运行一下看看",
                content="代码写好了？运行一下看看效果！调试也是编程的重要部分。",
                action_label="运行代码",
            )
        return None

    def _rule_deprecated_api(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """使用过时 API"""
        api_name = event.payload.get("api_name", "")
        replacement = event.payload.get("replacement", "")
        if not ledger.recently_exposed(event.student_id, f"deprecated:{api_name}", hours=4):
            msg = f"⚠️ 你使用了已弃用的方法 `{api_name}`"
            if replacement:
                msg += f"，推荐使用 `{replacement}` 替代"
            return ProactiveAction(
                action_type=ActionType.DEPRECATED_API_USED,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="方法已弃用",
                content=msg + "。点击了解新用法的详情。",
                action_label="查看替代方案",
            )
        return None

    def _rule_prerequisite_missing(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """前置知识缺失"""
        if not ledger.recently_exposed(event.student_id, "prerequisite_missing", hours=2):
            missing = event.payload.get("missing_topic", "基础知识")
            return ProactiveAction(
                action_type=ActionType.PREREQUISITE_MISSING,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="先巩固基础",
                content=f"要学这个内容，建议先巩固「{missing}」。我为你准备了一个快速回顾。",
                action_label="快速回顾",
            )
        return None

    def _rule_stuck_recommend_easier(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """卡壳降维推荐"""
        if not ledger.recently_exposed(event.student_id, "stuck_easier", hours=1):
            topic = event.payload.get("topic", "当前知识点")
            return ProactiveAction(
                action_type=ActionType.STUCK_RECOMMEND_EASIER,
                priority=MessagePriority.HIGH,
                delay_seconds=0,
                title="换个起点",
                content=f"「{topic}」确实有难度。推荐你先看看更基础的内容，再回来会轻松很多。",
                action_label="看基础内容",
            )
        return None

    # ------------------------------------------------------------------
    # Normal 规则
    # ------------------------------------------------------------------

    def _rule_health_reminder(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """学习时长健康提醒"""
        mins = rich.learning_state.today_minutes
        if mins > 120 and not ledger.recently_exposed(event.student_id, "health_break", hours=2):
            return ProactiveAction(
                action_type=ActionType.HEALTH_REMINDER,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="休息一下吧",
                content="你已经学习了 2 小时啦，起来活动一下，效率会更高哦~ 🌿",
                action_label="我知道了",
            )
        return None

    def _rule_daily_plan_incomplete(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """今日计划未完成"""
        progress = event.payload.get("plan_progress", 100)
        if progress < 70 and not ledger.recently_exposed(event.student_id, "daily_plan", hours=4):
            return ProactiveAction(
                action_type=ActionType.DAILY_PLAN_INCOMPLETE,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="今日计划",
                content=f"今天的计划完成度 {progress}%，要加把劲吗？还是调整到明天？",
                action_label="查看计划",
            )
        return None

    def _rule_path_deviation(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """学习路径偏离"""
        if not ledger.recently_exposed(event.student_id, "path_deviation", days=1):
            return ProactiveAction(
                action_type=ActionType.PATH_DEVIATION,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="路线调整？",
                content="你最近在基础上花了很多时间，原定本周开始进阶部分，需要调整计划吗？",
                action_label="调整计划",
            )
        return None

    def _rule_copy_paste(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """复制粘贴代码"""
        if not ledger.recently_exposed(event.student_id, "copy_paste", minutes=30):
            return ProactiveAction(
                action_type=ActionType.COPY_PASTE_DETECTED,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="亲手敲一遍",
                content="试着自己敲一遍代码，肌肉记忆会帮你记住语法。理解每一行的含义更重要！",
                action_label="好的",
            )
        return None

    def _rule_tab_switching(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """频繁切换标签页"""
        if not ledger.recently_exposed(event.student_id, "tab_switching", minutes=15):
            return ProactiveAction(
                action_type=ActionType.TAB_SWITCHING,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="保持专注",
                content="保持专注 25 分钟，然后休息 5 分钟，效率会更高。试试番茄钟！",
                action_label="开始番茄钟",
            )
        return None

    def _rule_repeated_error(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """重复同类错误"""
        error_type = event.payload.get("error_type", "")
        count = event.payload.get("error_count", 0)
        topic = f"error:{error_type}"
        if count >= 3 and not ledger.recently_exposed(event.student_id, topic, hours=4):
            return ProactiveAction(
                action_type=ActionType.REPEATED_ERROR_PATTERN,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="常见错误提醒",
                content=f"注意到你经常遇到「{error_type}」问题。这里有个小技巧可以帮你避免。",
                action_label="查看技巧",
            )
        return None

    def _rule_prerequisite_unlocked(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """前置任务已解锁"""
        if not ledger.recently_exposed(event.student_id, "prerequisite_unlocked", hours=24):
            next_topic = event.payload.get("next_topic", "新内容")
            return ProactiveAction(
                action_type=ActionType.PREREQUISITE_UNLOCKED,
                priority=MessagePriority.NORMAL,
                delay_seconds=5,
                title="🎉 新内容已解锁",
                content=f"恭喜你完成了前置部分！「{next_topic}」已经解锁，继续？",
                action_label="继续学习",
            )
        return None

    def _rule_learning_slump(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """学习低谷唤醒"""
        if not ledger.recently_exposed(event.student_id, "learning_slump", days=3):
            last_topic = rich.learning_state.last_study_topic or "上次学到的内容"
            return ProactiveAction(
                action_type=ActionType.LEARNING_SLUMP_RECALL,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="回来啦？",
                content=f"最近有点忙？哪怕每天 15 分钟，保持手感也很重要。从「{last_topic}」继续？",
                action_label="继续学习",
            )
        return None

    def _rule_progress_warning(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """周进度落后"""
        weekly = rich.learning_state.week_progress_percent
        if weekly < 50 and rich.learning_state.is_weekend:
            if not ledger.recently_exposed(event.student_id, "progress_warning", hours=24):
                return ProactiveAction(
                    action_type=ActionType.PROGRESS_WARNING,
                    priority=MessagePriority.NORMAL,
                    delay_seconds=0,
                    title="本周进度",
                    content=f"本周学习进度 {weekly}%，还有任务待完成哦，加油！",
                    action_label="查看任务",
                )
        return None

    # ------------------------------------------------------------------
    # Low 规则
    # ------------------------------------------------------------------

    def _rule_login_greeting(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """登录问候 / 回归召回"""
        days = rich.learning_state.days_since_last

        if days > 3:
            if not ledger.recently_exposed(event.student_id, "return_recall", days=1):
                return ProactiveAction(
                    action_type=ActionType.RETURN_RECALL,
                    priority=MessagePriority.LOW,
                    delay_seconds=3,
                    title="欢迎回来",
                    content=f"你已经 {days} 天没学习了，今天从哪开始？",
                    action_label="继续学习",
                )
        else:
            if not ledger.recently_exposed(event.student_id, "daily_greeting", hours=12):
                hour = datetime.utcnow().hour
                if 5 <= hour < 12:
                    greeting = "早上好"
                elif 12 <= hour < 18:
                    greeting = "下午好"
                else:
                    greeting = "晚上好"

                return ProactiveAction(
                    action_type=ActionType.DAILY_GREETING,
                    priority=MessagePriority.LOW,
                    delay_seconds=2,
                    title=greeting,
                    content=f"{greeting}！今天准备学什么？",
                    action_label="查看课程",
                )
        return None

    def _rule_milestone(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """里程碑庆祝"""
        milestone_type = event.payload.get("milestone_type", "")
        streak = rich.learning_state.streak_days

        if milestone_type == "streak" and streak > 0 and streak % 7 == 0:
            if not ledger.recently_exposed(event.student_id, f"streak:{streak}", days=1):
                return ProactiveAction(
                    action_type=ActionType.MILESTONE_CELEBRATION,
                    priority=MessagePriority.LOW,
                    delay_seconds=0,
                    title="🎉 太棒了",
                    content=f"连续学习 {streak} 天！太棒了，继续保持！",
                    action_label="谢谢",
                )

        if milestone_type == "chapter_complete":
            chapter = event.payload.get("chapter_name", "大章节")
            return ProactiveAction(
                action_type=ActionType.MILESTONE_CELEBRATION,
                priority=MessagePriority.LOW,
                delay_seconds=0,
                title="🎉 恭喜",
                content=f"恭喜完成「{chapter}」！这是学习路上的一个重要里程碑。",
                action_label="继续",
            )

        return None

    def _rule_idle_reminder(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """页面闲置提醒"""
        if not ledger.recently_exposed(event.student_id, "idle_reminder", minutes=30):
            return ProactiveAction(
                action_type=ActionType.HEALTH_REMINDER,
                priority=MessagePriority.LOW,
                delay_seconds=0,
                title="还在吗？",
                content="页面闲置一段时间了，需要我帮你回顾点什么吗？",
                action_label="帮我回顾",
            )
        return None

    # ------------------------------------------------------------------
    # 最佳时机规则
    # ------------------------------------------------------------------

    def _rule_golden_hour(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """黄金学习时间提醒"""
        if not ledger.recently_exposed(event.student_id, "golden_hour", hours=12):
            return ProactiveAction(
                action_type=ActionType.GOLDEN_HOUR,
                priority=MessagePriority.NORMAL,
                delay_seconds=0,
                title="状态最佳时段",
                content="根据你的学习记录，现在是你效率最高的时候，今天也学一会儿？",
                action_label="开始学习",
            )
        return None

    def _rule_fragment_time(
        self, event: TutorEvent, rich: RichContext, envelope: ResponseEnvelope, ledger: ActionLedger
    ) -> Optional[ProactiveAction]:
        """碎片时间利用"""
        if not ledger.recently_exposed(event.student_id, "fragment_time", hours=6):
            return ProactiveAction(
                action_type=ActionType.FRAGMENT_TIME,
                priority=MessagePriority.LOW,
                delay_seconds=0,
                title="5分钟复习",
                content="有 5 分钟空闲？做个快速复习题保持手感！",
                action_label="快速复习",
            )
        return None

    # ------------------------------------------------------------------
    # 通用规则（每次检查）
    # ------------------------------------------------------------------

    def _check_universal_rules(
        self,
        event: TutorEvent,
        rich: RichContext,
        envelope: ResponseEnvelope,
        ledger: ActionLedger,
    ) -> list[ProactiveAction]:
        """不受事件类型限制的通用检查"""
        actions = []

        # 检查是否需要复习提醒（即使不是 REVIEW_DUE 事件）
        for item in rich.sm2_due_items[:1]:
            topic = f"sm2:{item.knowledge_point}"
            if not ledger.recently_exposed(event.student_id, topic, minutes=60):
                link = Link(
                    type="internal",
                    title=f"复习：{item.knowledge_point}",
                    url=f"/review.html?item={item.id}",
                    description="根据你的记忆曲线，现在复习效果最好",
                )
                actions.append(ProactiveAction(
                    action_type=ActionType.REVIEW_REMINDER,
                    priority=MessagePriority.HIGH,
                    delay_seconds=30,
                    title="📚 顺便复习一下",
                    content=f"对了，{item.knowledge_point} 到了最佳复习时间，花 2 分钟？",
                    action_label="开始复习",
                    attached_link=link,
                    metadata={"topic": topic},
                ))

        return actions
