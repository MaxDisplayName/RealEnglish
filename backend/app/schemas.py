from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator


# ── Common ──
class UnifiedResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


# ── User ──
class UserResponse(BaseModel):
    id: str
    device_id: str
    level: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserRegisterRequest(BaseModel):
    device_id: str


# ── Auth ──
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "student"
    invite_code: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 2 or len(v) > 50:
            raise ValueError("用户名长度需在 2-50 之间")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密码长度至少 8 位")
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("密码需同时包含字母和数字")
        return v


class LoginRequest(BaseModel):
    login: str
    password: str
    role: Optional[str] = None


class UserOut(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: str = "student"
    level: Optional[str] = None
    teacher_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MergeDeviceRequest(BaseModel):
    device_id: str


# ── Answer ──
class AnswerSubmitRequest(BaseModel):
    question_id: str
    selected_option: int


class PlacementSubmitRequest(BaseModel):
    answers: list[AnswerSubmitRequest]


class AnswerSubmitResponse(BaseModel):
    is_correct: bool
    correct_answer: int
    explanation: str


class PlacementSubmitResponse(BaseModel):
    score: int
    total: int
    level: str
    details: list[dict]


# ── Clip ──
class ClipResponse(BaseModel):
    id: str
    bvid: str
    page: int
    start_sec: int
    end_sec: int
    iframe_url: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    difficulty: str
    dialogue_text: Optional[str] = None
    summary: Optional[str] = None
    subtitle_source: Optional[str] = None
    character_genders: Optional[dict] = None
    remark: Optional[str] = None
    imported_at: datetime

    class Config:
        from_attributes = True


class ClipListParams(BaseModel):
    difficulty: Optional[str] = None
    category: Optional[str] = None
    skip: int = 0
    limit: int = 20


# ── Question ──
class QuestionContent(BaseModel):
    question: str
    options: list[str]
    answer: int
    explanation: str


class QuestionResponse(BaseModel):
    id: str
    clip_id: str
    type: str
    difficulty: str
    content: QuestionContent
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateQuestionRequest(BaseModel):
    clip_id: str
    difficulty: str = "B"
    count: int = 3


# ── Teacher ──
class StudentSummary(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    level: Optional[str] = None
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    total_practices: int = 0
    accuracy: float = 0.0
    speaking_count: int = 0
    last_active: Optional[str] = None
    created_at: Optional[str] = None


class StudentListResponse(BaseModel):
    items: list[StudentSummary]
    total: int


class LevelDistribution(BaseModel):
    A: int = 0
    B: int = 0
    C: int = 0
    unset: int = 0


class DifficultyStat(BaseModel):
    total: int = 0
    correct: int = 0
    accuracy: float = 0.0


class WrongNoteSummary(BaseModel):
    question_id: str
    question: str
    wrong_times: int
    difficulty: str


class ActivityItem(BaseModel):
    date: str
    practice_count: int = 0
    speaking_count: int = 0


class SpeakingStats(BaseModel):
    total: int = 0
    avg_score: float = 0.0


class StudentDetail(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    level: Optional[str] = None
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    total_practices: int = 0
    accuracy: float = 0.0
    difficulty_stats: dict[str, DifficultyStat] = {}
    speaking_stats: SpeakingStats = SpeakingStats()
    recent_activity: list[ActivityItem] = []
    wrong_notes_summary: list[WrongNoteSummary] = []


class TeacherGroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeacherGroupCreate(TeacherGroupBase):
    pass


class TeacherGroupUpdate(TeacherGroupBase):
    pass


class StudentGroupAssignRequest(BaseModel):
    student_id: str
    group_id: Optional[str] = None


class BatchAssignRequest(BaseModel):
    student_ids: list[str]
    group_id: Optional[str] = None


class GroupMemberOut(BaseModel):
    id: str
    username: Optional[str] = None
    level: Optional[str] = None
    total_practices: int = 0
    accuracy: float = 0.0
    speaking_count: int = 0


class GroupStatsOut(BaseModel):
    total_students: int = 0
    avg_accuracy: float = 0.0
    avg_speaking_score: float = 0.0
    active_14d: int = 0
    level_distribution: LevelDistribution = LevelDistribution()


class GroupDetailOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    members: list[GroupMemberOut] = []
    stats: GroupStatsOut = GroupStatsOut()


class GroupComparisonItem(BaseModel):
    group_id: str
    group_name: str
    student_count: int = 0
    avg_accuracy: float = 0.0
    avg_speaking_score: float = 0.0
    active_rate: float = 0.0


# ── Free Talk ──
class FreeTalkStartResponse(BaseModel):
    conversation_id: str
    topic: str
    scenario: Optional[str] = None
    ai_role_name: Optional[str] = None
    user_role_name: Optional[str] = None
    first_message: str
    created_at: str


class FreeTalkRespondRequest(BaseModel):
    text: Optional[str] = None


class FreeTalkRespondResponse(BaseModel):
    reply: str
    transcript: Optional[str] = None
    audio_url: Optional[str] = None


class FreeTalkEvaluation(BaseModel):
    participation: float
    grammar: float
    vocabulary: float
    fluency: float
    overall: float
    summary: str
    suggestions: list[str]


class FreeTalkEndResponse(BaseModel):
    evaluation: FreeTalkEvaluation
    voice_used: bool
    message_count: int
    user_turn_count: int


class ConversationMessageOut(BaseModel):
    id: str
    role: str
    content: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: str


class FreeTalkSessionOut(BaseModel):
    id: str
    topic: str
    scenario: Optional[str] = None
    ai_role_name: Optional[str] = None
    user_role_name: Optional[str] = None
    status: str
    voice_used: bool
    evaluation_json: Optional[dict] = None
    feedback: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class FreeTalkHistoryResponse(BaseModel):
    conversation: FreeTalkSessionOut
    messages: list[ConversationMessageOut]


# ── Assistant Threads ──
class ThreadCreateRequest(BaseModel):
    role: str = "student"


class ThreadRenameRequest(BaseModel):
    title: str


class ThreadOut(BaseModel):
    id: str
    title: str
    role: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ThreadListResponse(BaseModel):
    threads: list[ThreadOut]


# ── Video ──
class VideoUrlResponse(BaseModel):
    url: str
    format: str = "mp4"
    quality: int = 32
    expires_at: float


# ── Teacher Dashboard ──
class TrendItem(BaseModel):
    date: str
    practice_count: int = 0
    speaking_count: int = 0
    correct_rate: float = 0.0
    avg_speaking_score: float = 0.0


class TeacherDashboardData(BaseModel):
    total_students: int = 0
    today_active_students: int = 0
    total_practices_today: int = 0
    total_speaking_today: int = 0
    overall_accuracy: float = 0.0
    trend: list[TrendItem] = []
    level_distribution: LevelDistribution = LevelDistribution()


# ── Communication ──
class AnnouncementCreate(BaseModel):
    title: str
    content: str
    target_type: str = "all"
    target_group_id: Optional[str] = None
    is_pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: str
    content: str
    target_type: str = "all"
    target_group_id: Optional[str] = None


class AnnouncementOut(BaseModel):
    id: str
    teacher_id: str
    title: str
    content: str
    target_type: str
    target_group_id: Optional[str] = None
    is_pinned: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageSend(BaseModel):
    subject: Optional[str] = None
    content: str
    receiver_id: Optional[str] = None
    group_id: Optional[str] = None
    parent_id: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    sender_id: str
    sender_name: str = ""
    receiver_id: Optional[str] = None
    subject: Optional[str] = None
    content: str
    is_read: bool = False
    parent_id: Optional[str] = None
    created_at: Optional[str] = None


# ── Task ──
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    target_type: str = "all"
    target_group_id: Optional[str] = None
    practice_goal: int = 0
    speaking_goal: int = 0
    free_talk_goal: int = 0
    clip_goal: int = 0
    accuracy_goal: Optional[float] = None
    deadline: Optional[str] = None


class TaskUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    practice_goal: int = 0
    speaking_goal: int = 0
    free_talk_goal: int = 0
    clip_goal: int = 0
    accuracy_goal: Optional[float] = None
    deadline: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    teacher_id: str
    title: str
    description: Optional[str] = None
    target_type: str
    target_group_id: Optional[str] = None
    practice_goal: int = 0
    speaking_goal: int = 0
    free_talk_goal: int = 0
    clip_goal: int = 0
    accuracy_goal: Optional[float] = None
    deadline: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None
    completed_count: int = 0
    total_count: int = 0


class TaskProgressOut(BaseModel):
    student_id: str
    student_name: str = ""
    practice_done: int = 0
    speaking_done: int = 0
    free_talk_done: int = 0
    clips_done: int = 0
    current_accuracy: Optional[float] = None
    is_completed: bool = False
    completed_at: Optional[str] = None


class StudentTaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    practice_goal: int = 0
    speaking_goal: int = 0
    free_talk_goal: int = 0
    clip_goal: int = 0
    accuracy_goal: Optional[float] = None
    deadline: Optional[str] = None
    status: str
    practice_done: int = 0
    speaking_done: int = 0
    free_talk_done: int = 0
    clips_done: int = 0
    is_completed: bool = False

class MarkReadRequest(BaseModel):
    message_id: int
