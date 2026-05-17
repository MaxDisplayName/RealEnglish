import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

from app.time_utils import beijing_now

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    avatar = Column(String(255), nullable=True)
    role = Column(String(10), nullable=False, default="student")
    is_active = Column(Boolean, default=True)
    group_id = Column(String(36), ForeignKey("teacher_groups.id"), nullable=True, index=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    device_id = Column(String(36), unique=True, nullable=True, index=True)
    level = Column(String(1), nullable=True)
    invite_code = Column(String(4), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class VideoClipModel(Base):
    __tablename__ = "video_clips"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bvid = Column(String(20), nullable=False)
    page = Column(Integer, nullable=False)
    start_sec = Column(Integer, nullable=False)
    end_sec = Column(Integer, nullable=False)
    iframe_url = Column(Text, nullable=True)
    title = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    difficulty = Column(String(1), nullable=False)
    dialogue_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    subtitle_source = Column(String(50), nullable=True)
    character_genders = Column(JSON, nullable=True)
    remark = Column(Text, nullable=True)
    imported_at = Column(DateTime, default=beijing_now)


class QuestionModel(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clip_id = Column(String(36), ForeignKey("video_clips.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(10), nullable=False, default="part2")
    difficulty = Column(String(1), nullable=False)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=beijing_now)


class PracticeRecordModel(Base):
    __tablename__ = "practice_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    selected_option = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime, default=beijing_now)


class SpeakingRecordModel(Base):
    __tablename__ = "speaking_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    clip_id = Column(String(36), ForeignKey("video_clips.id"), nullable=True)
    mode = Column(String(20), nullable=False, default="repeat")
    reference_text = Column(Text, nullable=True)
    audio_url = Column(String(500), nullable=True)
    score_json = Column(JSON, nullable=True)
    feedback = Column(Text, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=beijing_now)


class TeacherGroupModel(Base):
    __tablename__ = "teacher_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class FreeConversationModel(Base):
    __tablename__ = "free_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    scenario = Column(Text, nullable=True)
    ai_role_name = Column(String(100), nullable=True)
    user_role_name = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    evaluation_json = Column(JSON, nullable=True)
    feedback = Column(Text, nullable=True)
    voice_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=beijing_now)
    completed_at = Column(DateTime, nullable=True)


class ConversationMessageModel(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("free_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=True)
    audio_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=beijing_now)


class AssistantThreadModel(Base):
    __tablename__ = "assistant_threads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(10), nullable=False)
    title = Column(String(100), nullable=False, default="新对话")
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class ThreadMessageModel(Base):
    __tablename__ = "thread_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    thread_id = Column(String(36), ForeignKey("assistant_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=beijing_now)


class AnnouncementModel(Base):
    __tablename__ = "announcements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    target_type = Column(String(20), default="all")  # "all" | "group"
    target_group_id = Column(String(36), ForeignKey("teacher_groups.id"), nullable=True, index=True)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("teacher_groups.id"), nullable=True, index=True)
    subject = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    parent_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=beijing_now)


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_type = Column(String(20), default="all")  # "all" | "group"
    target_group_id = Column(String(36), ForeignKey("teacher_groups.id"), nullable=True, index=True)
    practice_goal = Column(Integer, default=0)
    speaking_goal = Column(Integer, default=0)
    free_talk_goal = Column(Integer, default=0)
    clip_goal = Column(Integer, default=0)
    accuracy_goal = Column(Float, nullable=True)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")  # "active" | "completed" | "cancelled"
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class TaskProgressModel(Base):
    __tablename__ = "task_progress"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    practice_done = Column(Integer, default=0)
    speaking_done = Column(Integer, default=0)
    free_talk_done = Column(Integer, default=0)
    clips_done = Column(Integer, default=0)
    current_accuracy = Column(Float, nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    __table_args__ = (
        UniqueConstraint("task_id", "student_id", name="uq_task_student"),
    )


class UserVocabularyModel(Base):
    __tablename__ = "user_vocabulary"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    word = Column(String(100), nullable=False)
    clip_id = Column(String(36), ForeignKey("video_clips.id"), nullable=True)
    definition = Column(Text, nullable=True)
    mastered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=beijing_now)

    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_user_word"),
    )
