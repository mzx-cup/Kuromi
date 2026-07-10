from app.models.base import Base
from app.models.user import User, StudentProfile, LoginRecord, Profile
from app.models.preferences import UserPreference, UserSetting, UserTheme
from app.models.learning import (
    StudySession,
    LearningRecord,
    UserStats,
    LearningGoal,
    WeeklySummary,
)
from app.models.course_progress import (
    CourseProgress,
    LearningPath,
    LearningPathNode,
    UserEvaluation,
    CourseGenerationStatus,
)
from app.models.course import (
    Course,
    Chapter,
    SubChapter,
    KnowledgePoint,
    SceneOutline,
    Slide,
    Subject,
)
from app.models.classroom import ClassroomSession, QuizRecord, AgentTurnRecord
from app.models.message import Message, ConversationSummary
from app.models.knowledge import (
    KnowledgeNode,
    KnowledgeRelation,
    KnowledgeReview,
    KnowledgeRecord,
    KnowledgePending,
)
from app.models.focus import (
    FocusSession,
    FocusEvent,
    UserFocusHistory,
)
from app.models.gamification import (
    UserGarden,
    UserPet,
    UserAchievement,
    UserEcoData,
)
from app.models.chat import (
    ChatMessage,
    ChatSummary,
    ChatTurnRecord,
    UserMemory,
)

__all__ = [
    "Base",
    "User",
    "StudentProfile",
    "LoginRecord",
    "Profile",
    "UserPreference",
    "UserSetting",
    "UserTheme",
    "StudySession",
    "LearningRecord",
    "UserStats",
    "LearningGoal",
    "WeeklySummary",
    "CourseProgress",
    "LearningPath",
    "LearningPathNode",
    "UserEvaluation",
    "CourseGenerationStatus",
    "Course",
    "Chapter",
    "SubChapter",
    "KnowledgePoint",
    "SceneOutline",
    "Slide",
    "Subject",
    "ClassroomSession",
    "QuizRecord",
    "AgentTurnRecord",
    "Message",
    "ConversationSummary",
    "KnowledgeNode",
    "KnowledgeRelation",
    "KnowledgeReview",
    "KnowledgeRecord",
    "KnowledgePending",
    "FocusSession",
    "FocusEvent",
    "UserFocusHistory",
    "UserGarden",
    "UserPet",
    "UserAchievement",
    "UserEcoData",
    "ChatMessage",
    "ChatSummary",
    "ChatTurnRecord",
    "UserMemory",
]
