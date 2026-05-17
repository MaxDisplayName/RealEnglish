import random
from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.time_utils import beijing_now

from app.models import (
    PracticeRecordModel,
    QuestionModel,
    SpeakingRecordModel,
    TeacherGroupModel,
    UserModel,
    UserVocabularyModel,
    VideoClipModel,
)


# ── User CRUD ──
def get_or_create_user(db: Session, device_id: str) -> UserModel:
    user = db.query(UserModel).filter(UserModel.device_id == device_id).first()
    if not user:
        user = UserModel(device_id=device_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_user_by_device_id(db: Session, device_id: str) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.device_id == device_id).first()


def get_user_by_id(db: Session, user_id: str) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_login(db: Session, login: str, role: str | None = None) -> UserModel | None:
    query = db.query(UserModel).filter(
        or_(UserModel.username == login, UserModel.email == login)
    )
    if role:
        query = query.filter(UserModel.role == role)
    return query.first()


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.email == email).first()


def get_user_by_username(db: Session, username: str) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.username == username).first()


def create_user(
    db: Session, username: str, email: str, hashed_password: str, role: str = "student",
    teacher_id: str | None = None, group_id: str | None = None,
) -> UserModel:
    user = UserModel(username=username, email=email, hashed_password=hashed_password,
                     role=role, teacher_id=teacher_id, group_id=group_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def assign_user_group(db: Session, user_id: str, group_id: str | None) -> UserModel | None:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user:
        user.group_id = group_id
        db.commit()
        db.refresh(user)
    return user


def update_user_level(db: Session, user_id: str, level: str) -> UserModel:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user:
        user.level = level
        db.commit()
        db.refresh(user)
    return user


def merge_device_records(db: Session, user_id: str, device_id: str) -> bool:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        return False
    db.query(SpeakingRecordModel).filter(
        SpeakingRecordModel.user_id == device_id
    ).update({"user_id": user_id})
    db.query(PracticeRecordModel).filter(
        PracticeRecordModel.user_id == device_id
    ).update({"user_id": user_id})
    if user.device_id == device_id:
        user.device_id = None
    db.commit()
    return True


# ── Clip CRUD ──
def get_clips(
    db: Session, difficulty: str | None = None, category: str | None = None,
    skip: int = 0, limit: int = 20,
) -> list[VideoClipModel]:
    query = db.query(VideoClipModel)
    if difficulty:
        query = query.filter(VideoClipModel.difficulty == difficulty)
    if category:
        query = query.filter(VideoClipModel.category == category)
    return query.order_by(VideoClipModel.difficulty.asc()).offset(skip).limit(limit).all()


def get_clip_by_id(db: Session, clip_id: str) -> VideoClipModel | None:
    return db.query(VideoClipModel).filter(VideoClipModel.id == clip_id).first()


def get_clip_count(db: Session) -> int:
    return db.query(func.count(VideoClipModel.id)).scalar()


def get_clips_by_ids(db: Session, clip_ids: list[str]) -> dict[str, VideoClipModel]:
    clips = db.query(VideoClipModel).filter(VideoClipModel.id.in_(clip_ids)).all()
    return {str(c.id): c for c in clips}


# ── Question CRUD ──
def get_placement_questions(db: Session) -> list[QuestionModel]:
    a_questions = db.query(QuestionModel).filter(QuestionModel.difficulty == "A").order_by(func.random()).limit(3).all()
    b_questions = db.query(QuestionModel).filter(QuestionModel.difficulty == "B").order_by(func.random()).limit(4).all()
    c_questions = db.query(QuestionModel).filter(QuestionModel.difficulty == "C").order_by(func.random()).limit(3).all()
    all_questions = a_questions + b_questions + c_questions
    random.shuffle(all_questions)
    return all_questions


def get_questions_by_clip(db: Session, clip_id: str) -> list[QuestionModel]:
    return db.query(QuestionModel).filter(QuestionModel.clip_id == clip_id).all()


def get_question_by_id(db: Session, question_id: str) -> QuestionModel | None:
    return db.query(QuestionModel).filter(QuestionModel.id == question_id).first()


def create_question(db: Session, question_data: dict) -> QuestionModel:
    question = QuestionModel(
        clip_id=question_data["clip_id"],
        type=question_data.get("type", "part2"),
        difficulty=question_data["difficulty"],
        content=question_data["content"],
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_question_count(db: Session) -> int:
    return db.query(func.count(QuestionModel.id)).scalar()


# ── Practice Record CRUD ──
def create_record(
    db: Session, user_id: str, question_id: str, selected_option: int, is_correct: bool,
) -> PracticeRecordModel:
    record = PracticeRecordModel(
        user_id=user_id, question_id=question_id,
        selected_option=selected_option, is_correct=is_correct,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_wrong_notes(db: Session, user_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
    records = (
        db.query(PracticeRecordModel)
        .filter(PracticeRecordModel.user_id == user_id, PracticeRecordModel.is_correct == False)  # noqa: E712
        .order_by(PracticeRecordModel.answered_at.desc())
        .offset(skip).limit(limit).all()
    )
    result = []
    for r in records:
        question = db.query(QuestionModel).filter(QuestionModel.id == r.question_id).first()
        if not question:
            continue
        result.append({
            "id": str(r.id),
            "question_id": str(r.question_id),
            "selected_option": r.selected_option,
            "answered_at": r.answered_at.isoformat() if r.answered_at else None,
            "question_type": question.type,
            "difficulty": question.difficulty,
            "content": {
                "question": question.content["question"],
                "options": question.content["options"],
                "answer": question.content["answer"],
                "explanation": question.content.get("explanation", ""),
            },
        })
    return result


def get_wrong_note_count(db: Session, user_id: str) -> int:
    return (
        db.query(func.count(PracticeRecordModel.id))
        .filter(PracticeRecordModel.user_id == user_id, PracticeRecordModel.is_correct == False)  # noqa: E712
        .scalar()
    )


def get_practice_stats(db: Session, user_id: str) -> dict:
    records = db.query(PracticeRecordModel).filter(PracticeRecordModel.user_id == user_id).all()
    total = len(records)
    correct = sum(1 for r in records if r.is_correct)
    accuracy = round(correct / total * 100, 1) if total > 0 else 0
    difficulty_stats = {}
    for difficulty in ["A", "B", "C"]:
        diff_records = []
        for r in records:
            q = db.query(QuestionModel).filter(QuestionModel.id == r.question_id).first()
            if q and q.difficulty == difficulty:
                diff_records.append(r)
        d_total = len(diff_records)
        d_correct = sum(1 for r in diff_records if r.is_correct)
        difficulty_stats[difficulty] = {
            "total": d_total, "correct": d_correct,
            "accuracy": round(d_correct / d_total * 100, 1) if d_total > 0 else 0,
        }
    return {"total": total, "correct": correct, "accuracy": accuracy, "difficulty_stats": difficulty_stats}


def get_placement_records(db: Session, user_id: str) -> list[PracticeRecordModel]:
    return db.query(PracticeRecordModel).filter(PracticeRecordModel.user_id == user_id).all()


# ── Teacher CRUD ──
def _teacher_student_query(db: Session, teacher_id: str):
    return (
        db.query(UserModel, TeacherGroupModel.name.label("group_name"))
        .outerjoin(TeacherGroupModel, UserModel.group_id == TeacherGroupModel.id)
        .filter(
            UserModel.role == "student",
            or_(
                UserModel.teacher_id == teacher_id,
                TeacherGroupModel.teacher_id == teacher_id,
            ),
        )
    )


def get_students(
    db: Session, teacher_id: str, skip: int = 0, limit: int = 20,
    keyword: str | None = None, group_id: str | None = None,
) -> tuple[list[dict], int]:
    query = _teacher_student_query(db, teacher_id)
    if keyword:
        query = query.filter(or_(UserModel.username.ilike(f"%{keyword}%"), UserModel.email.ilike(f"%{keyword}%")))
    if group_id:
        query = query.filter(UserModel.group_id == group_id)
    total = query.count()
    users = query.order_by(UserModel.created_at.desc()).offset(skip).limit(limit).all()
    items = []
    for user, group_name in users:
        uid = str(user.id)
        practice_count = db.query(func.count(PracticeRecordModel.id)).filter(PracticeRecordModel.user_id == uid).scalar() or 0
        correct_count = db.query(func.count(PracticeRecordModel.id)).filter(PracticeRecordModel.user_id == uid, PracticeRecordModel.is_correct.is_(True)).scalar() or 0
        speaking_count = db.query(func.count(SpeakingRecordModel.id)).filter(SpeakingRecordModel.user_id == uid).scalar() or 0
        accuracy = round(correct_count / practice_count * 100, 1) if practice_count > 0 else 0.0
        last_practice = db.query(func.max(PracticeRecordModel.answered_at)).filter(PracticeRecordModel.user_id == uid).scalar()
        last_speaking = db.query(func.max(SpeakingRecordModel.created_at)).filter(SpeakingRecordModel.user_id == uid).scalar()
        last_active = None
        if last_practice and last_speaking:
            last_active = max(last_practice, last_speaking).isoformat()
        elif last_practice:
            last_active = last_practice.isoformat()
        elif last_speaking:
            last_active = last_speaking.isoformat()
        items.append({
            "id": uid, "username": user.username, "email": user.email,
            "level": user.level, "group_id": user.group_id, "group_name": group_name,
            "total_practices": practice_count, "accuracy": accuracy,
            "speaking_count": speaking_count, "last_active": last_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
    return items, total


def get_level_distribution(db: Session, teacher_id: str, group_id: str | None = None) -> dict[str, int]:
    query = (
        db.query(UserModel.level, func.count(UserModel.id))
        .outerjoin(TeacherGroupModel, UserModel.group_id == TeacherGroupModel.id)
        .filter(UserModel.role == "student", or_(UserModel.teacher_id == teacher_id, TeacherGroupModel.teacher_id == teacher_id))
    )
    if group_id:
        query = query.filter(UserModel.group_id == group_id)
    rows = query.group_by(UserModel.level).all()
    result = {"A": 0, "B": 0, "C": 0, "unset": 0}
    for level, count in rows:
        if level in result:
            result[level] = count
        else:
            result["unset"] += count
    return result


def get_student_detail(db: Session, teacher_id: str, student_id: str) -> dict | None:
    user = (
        db.query(UserModel)
        .outerjoin(TeacherGroupModel, UserModel.group_id == TeacherGroupModel.id)
        .filter(UserModel.id == student_id, UserModel.role == "student", or_(UserModel.teacher_id == teacher_id, TeacherGroupModel.teacher_id == teacher_id))
        .first()
    )
    if not user:
        return None
    records = db.query(PracticeRecordModel).filter(PracticeRecordModel.user_id == student_id).all()
    total = len(records)
    correct = sum(1 for r in records if r.is_correct)
    accuracy = round(correct / total * 100, 1) if total > 0 else 0.0
    question_map = {
        str(q.id): q
        for q in db.query(QuestionModel).filter(QuestionModel.id.in_([r.question_id for r in records] or [""])).all()
    }
    difficulty_stats = {}
    for difficulty in ["A", "B", "C"]:
        diff_records = [r for r in records if question_map.get(r.question_id) and question_map[r.question_id].difficulty == difficulty]
        d_total = len(diff_records)
        d_correct = sum(1 for r in diff_records if r.is_correct)
        difficulty_stats[difficulty] = {
            "total": d_total, "correct": d_correct,
            "accuracy": round(d_correct / d_total * 100, 1) if d_total > 0 else 0.0,
        }
    speaking_records = db.query(SpeakingRecordModel).filter(SpeakingRecordModel.user_id == student_id).all()
    speaking_scores = [
        float(r.score_json["total_score"])
        for r in speaking_records if r.score_json and "total_score" in r.score_json
    ]
    speaking_samples = []
    for r in speaking_records[-5:]:
        speaking_samples.append({
            "id": str(r.id), "mode": r.mode, "reference_text": r.reference_text,
            "audio_url": r.audio_url, "score_json": r.score_json, "feedback": r.feedback,
            "duration_sec": r.duration_sec,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    speaking_samples.reverse()

    return {
        "id": student_id, "username": user.username, "email": user.email,
        "level": user.level, "group_id": user.group_id,
        "group_name": db.query(TeacherGroupModel.name).filter(TeacherGroupModel.id == user.group_id).scalar() if user.group_id else None,
        "total_practices": total, "accuracy": accuracy, "difficulty_stats": difficulty_stats,
        "speaking_stats": {
            "total": len(speaking_records),
            "avg_score": round(sum(speaking_scores) / len(speaking_scores), 1) if speaking_scores else 0.0,
        },
        "recent_activity": _get_recent_activity(db, student_id),
        "wrong_notes_summary": _get_wrong_notes_summary(db, student_id),
        "speaking_samples": speaking_samples,
    }


def list_teacher_groups_with_counts(db: Session, teacher_id: str) -> list[dict]:
    rows = (
        db.query(TeacherGroupModel.id, TeacherGroupModel.name, TeacherGroupModel.description, func.count(UserModel.id).label("student_count"))
        .outerjoin(UserModel, UserModel.group_id == TeacherGroupModel.id)
        .filter(TeacherGroupModel.teacher_id == teacher_id)
        .group_by(TeacherGroupModel.id, TeacherGroupModel.name, TeacherGroupModel.description)
        .order_by(TeacherGroupModel.created_at.asc())
        .all()
    )
    return [{"id": gid, "name": name, "description": desc, "student_count": cnt} for gid, name, desc, cnt in rows]


def _get_recent_activity(db: Session, student_id: str, days: int = 14) -> list[dict]:
    since = beijing_now() - timedelta(days=days)
    dates_map: dict[str, dict] = {}
    for date_str, count in (
        db.query(func.date(PracticeRecordModel.answered_at), func.count(PracticeRecordModel.id))
        .filter(PracticeRecordModel.user_id == student_id, PracticeRecordModel.answered_at >= since)
        .group_by(func.date(PracticeRecordModel.answered_at)).all()
    ):
        dates_map.setdefault(str(date_str), {"practice_count": 0, "speaking_count": 0})
        dates_map[str(date_str)]["practice_count"] = count
    for date_str, count in (
        db.query(func.date(SpeakingRecordModel.created_at), func.count(SpeakingRecordModel.id))
        .filter(SpeakingRecordModel.user_id == student_id, SpeakingRecordModel.created_at >= since)
        .group_by(func.date(SpeakingRecordModel.created_at)).all()
    ):
        dates_map.setdefault(str(date_str), {"practice_count": 0, "speaking_count": 0})
        dates_map[str(date_str)]["speaking_count"] = count
    result = []
    for index in range(days):
        day = (beijing_now() - timedelta(days=days - 1 - index)).strftime("%Y-%m-%d")
        entry = dates_map.get(day, {"practice_count": 0, "speaking_count": 0})
        entry["date"] = day
        result.append(entry)
    return result


def _get_wrong_notes_summary(db: Session, student_id: str, limit: int = 5) -> list[dict]:
    wrong_rows = (
        db.query(PracticeRecordModel.question_id, func.count(PracticeRecordModel.id).label("wrong_times"))
        .filter(PracticeRecordModel.user_id == student_id, PracticeRecordModel.is_correct.is_(False))
        .group_by(PracticeRecordModel.question_id)
        .order_by(func.count(PracticeRecordModel.id).desc()).limit(limit).all()
    )
    result = []
    for question_id, wrong_times in wrong_rows:
        question = db.query(QuestionModel).filter(QuestionModel.id == question_id).first()
        if question:
            result.append({"question_id": question_id, "question": question.content.get("question", ""), "wrong_times": wrong_times, "difficulty": question.difficulty or ""})
    return result


# ── Teacher Group CRUD ──
def list_teacher_groups(db: Session, teacher_id: str) -> list[TeacherGroupModel]:
    return db.query(TeacherGroupModel).filter(TeacherGroupModel.teacher_id == teacher_id).order_by(TeacherGroupModel.created_at.asc()).all()


def get_teacher_group(db: Session, group_id: str, teacher_id: str) -> TeacherGroupModel | None:
    return db.query(TeacherGroupModel).filter(TeacherGroupModel.id == group_id, TeacherGroupModel.teacher_id == teacher_id).first()


def create_teacher_group(db: Session, teacher_id: str, name: str, description: str | None = None) -> TeacherGroupModel:
    group = TeacherGroupModel(teacher_id=teacher_id, name=name, description=description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_teacher_group(db: Session, group: TeacherGroupModel, name: str, description: str | None = None) -> TeacherGroupModel:
    group.name = name
    group.description = description
    db.commit()
    db.refresh(group)
    return group


# ── Student Dashboard ──

def _count_today(db: Session, model, user_id: str, date_col) -> int:
    """统计今日某表的记录数"""
    today = beijing_now().date()
    return db.query(func.count(model.id)).filter(
        model.user_id == user_id,
        func.date(date_col) == today,
    ).scalar() or 0


def _distinct_clips_today(db: Session, user_id: str) -> int:
    """统计今日练习过的不同片段数"""
    today = beijing_now().date()
    count = (
        db.query(func.count(func.distinct(QuestionModel.clip_id)))
        .join(PracticeRecordModel, PracticeRecordModel.question_id == QuestionModel.id)
        .filter(
            PracticeRecordModel.user_id == user_id,
            func.date(PracticeRecordModel.answered_at) == today,
        )
        .scalar()
    ) or 0
    return count


def get_student_dashboard_data(db: Session, user_id: str) -> dict:
    """返回学习概览页所需的所有聚合数据"""
    today = beijing_now().date()
    today_practice_count = _count_today(db, PracticeRecordModel, user_id, PracticeRecordModel.answered_at)
    today_clip_count = _distinct_clips_today(db, user_id)
    today_speaking_count = _count_today(db, SpeakingRecordModel, user_id, SpeakingRecordModel.created_at)

    # 今日口语总时长（秒）
    today_duration = (
        db.query(func.coalesce(func.sum(SpeakingRecordModel.duration_sec), 0))
        .filter(
            SpeakingRecordModel.user_id == user_id,
            func.date(SpeakingRecordModel.created_at) == today,
        )
        .scalar()
    ) or 0

    # 近 7 天每日活跃数据
    weekly_activity = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        practice_day = (
            db.query(func.count(PracticeRecordModel.id))
            .filter(PracticeRecordModel.user_id == user_id, func.date(PracticeRecordModel.answered_at) == d)
            .scalar()
        ) or 0
        correct_day = (
            db.query(func.count(PracticeRecordModel.id))
            .filter(PracticeRecordModel.user_id == user_id, func.date(PracticeRecordModel.answered_at) == d, PracticeRecordModel.is_correct.is_(True))
            .scalar()
        ) or 0
        speaking_day = (
            db.query(func.count(SpeakingRecordModel.id))
            .filter(SpeakingRecordModel.user_id == user_id, func.date(SpeakingRecordModel.created_at) == d)
            .scalar()
        ) or 0
        avg_score_result = (
            db.query(func.avg(SpeakingRecordModel.score_json))
            .filter(SpeakingRecordModel.user_id == user_id, func.date(SpeakingRecordModel.created_at) == d)
            .scalar()
        )
        # score_json is stored as JSON; compute avg in Python
        speaking_recs = (
            db.query(SpeakingRecordModel.score_json)
            .filter(SpeakingRecordModel.user_id == user_id, func.date(SpeakingRecordModel.created_at) == d)
            .all()
        )
        avg_score = 0.0
        if speaking_recs:
            import json as _json
            scores = []
            for (sj,) in speaking_recs:
                if sj:
                    try:
                        s = _json.loads(sj) if isinstance(sj, str) else sj
                        if isinstance(s, dict) and "total_score" in s:
                            scores.append(float(s["total_score"]))
                    except Exception:
                        pass
            avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        duration_day = (
            db.query(func.coalesce(func.sum(SpeakingRecordModel.duration_sec), 0))
            .filter(SpeakingRecordModel.user_id == user_id, func.date(SpeakingRecordModel.created_at) == d)
            .scalar()
        ) or 0

        weekly_activity.append({
            "date": d.isoformat(),
            "practice_count": practice_day,
            "correct_count": correct_day,
            "speaking_count": speaking_day,
            "avg_speaking_score": avg_score,
            "duration_min": round(duration_day / 60, 1),
        })

    # 近 6 个月热力图数据
    heatmap_data = []
    for i in range(180):
        d = today - timedelta(days=i)
        practice_c = (
            db.query(func.count(PracticeRecordModel.id))
            .filter(PracticeRecordModel.user_id == user_id, func.date(PracticeRecordModel.answered_at) == d)
            .scalar()
        ) or 0
        speaking_c = (
            db.query(func.count(SpeakingRecordModel.id))
            .filter(SpeakingRecordModel.user_id == user_id, func.date(SpeakingRecordModel.created_at) == d)
            .scalar()
        ) or 0
        heatmap_data.append({"date": d.isoformat(), "count": practice_c + speaking_c})

    # 推荐片段
    recommended = recommend_clips(db, user_id, limit=6)
    # 如果没有练习记录，返回最新片段
    if not recommended:
        all_clips = db.query(VideoClipModel).order_by(VideoClipModel.imported_at.desc()).limit(6).all()
        recommended = [_clip_to_dict(c) for c in all_clips]

    return {
        "today_practice_count": today_practice_count,
        "today_clip_count": today_clip_count,
        "today_speaking_count": today_speaking_count,
        "today_total_duration_min": round(today_duration / 60, 1),
        "weekly_activity": weekly_activity,
        "heatmap_data": heatmap_data,
        "recommended_clips": recommended,
    }


def _clip_to_dict(c: VideoClipModel) -> dict:
    return {
        "id": str(c.id), "bvid": c.bvid, "page": c.page,
        "start_sec": c.start_sec, "end_sec": c.end_sec,
        "title": c.title, "category": c.category, "difficulty": c.difficulty,
        "summary": c.summary or "",
    }


def recommend_clips(db: Session, user_id: str, limit: int = 6) -> list[dict]:
    """基于用户等级和练习历史推荐片段"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        return []

    user_level = user.level or "B"

    # 用户已练习过的片段 ID
    practiced_ids = set()
    rows = (
        db.query(QuestionModel.clip_id)
        .join(PracticeRecordModel, PracticeRecordModel.question_id == QuestionModel.id)
        .filter(PracticeRecordModel.user_id == user_id)
        .distinct()
        .all()
    )
    for (cid,) in rows:
        practiced_ids.add(cid)

    # 偏好类别: 统计已练习片段的 category
    cat_counts = {}
    if practiced_ids:
        cat_rows = (
            db.query(VideoClipModel.category, func.count(VideoClipModel.id))
            .filter(VideoClipModel.id.in_(practiced_ids))
            .group_by(VideoClipModel.category)
            .all()
        )
        for cat, cnt in cat_rows:
            if cat:
                cat_counts[cat] = cnt
    top_cats = sorted(cat_counts, key=cat_counts.get, reverse=True)[:2]

    # 评分所有片段
    all_clips = db.query(VideoClipModel).all()
    scored = []
    for c in all_clips:
        score = 0
        # 难度匹配
        if c.difficulty == user_level:
            score += 3
        elif c.difficulty and user_level:
            diff_order = {"A": 0, "B": 1, "C": 2}
            if abs(diff_order.get(c.difficulty, 1) - diff_order.get(user_level, 1)) == 1:
                score += 1
        # 类别匹配
        if c.category in top_cats:
            score += 2
        # 未练习过
        if str(c.id) not in practiced_ids:
            score += 1

        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_clip_to_dict(c) for _, c in scored[:limit]]


def _get_teacher_student_ids(db: Session, teacher_id: str, group_id: str | None = None) -> list[str]:
    """获取教师关联的学生ID列表，可选按分组过滤。"""
    group_ids_query = db.query(TeacherGroupModel.id).filter(TeacherGroupModel.teacher_id == teacher_id)
    group_ids = [g[0] for g in group_ids_query.all()]

    query = db.query(UserModel.id).filter(UserModel.role == "student")
    if group_id:
        query = query.filter(UserModel.group_id == group_id)
    else:
        conditions = [UserModel.teacher_id == teacher_id]
        if group_ids:
            conditions.append(UserModel.group_id.in_(group_ids))
        query = query.filter(or_(*conditions))
    return [u[0] for u in query.all()]


def get_teacher_dashboard_stats(db: Session, teacher_id: str, group_id: str | None = None) -> dict:
    """教师看板聚合数据：统计卡片 + 近14天趋势 + 等级分布。"""
    from datetime import date, timedelta

    student_ids = _get_teacher_student_ids(db, teacher_id, group_id)
    total_students = len(student_ids)
    today_val = date.today()

    # 今日统计
    today_practice = 0
    today_speaking = 0
    active_student_ids = set()

    if student_ids:
        today_practice = (
            db.query(func.count(PracticeRecordModel.id))
            .filter(
                PracticeRecordModel.user_id.in_(student_ids),
                func.date(PracticeRecordModel.answered_at) == today_val,
            )
            .scalar()
        ) or 0
        today_speaking = (
            db.query(func.count(SpeakingRecordModel.id))
            .filter(
                SpeakingRecordModel.user_id.in_(student_ids),
                func.date(SpeakingRecordModel.created_at) == today_val,
            )
            .scalar()
        ) or 0

        # 今日活跃学生
        practice_users = set()
        for (uid,) in (
            db.query(PracticeRecordModel.user_id)
            .filter(
                PracticeRecordModel.user_id.in_(student_ids),
                func.date(PracticeRecordModel.answered_at) == today_val,
            )
            .distinct()
            .all()
        ):
            practice_users.add(uid)
        for (uid,) in (
            db.query(SpeakingRecordModel.user_id)
            .filter(
                SpeakingRecordModel.user_id.in_(student_ids),
                func.date(SpeakingRecordModel.created_at) == today_val,
            )
            .distinct()
            .all()
        ):
            practice_users.add(uid)
        active_student_ids = practice_users

    # 总正确率
    overall_accuracy = 0.0
    if student_ids:
        total_all = (
            db.query(func.count(PracticeRecordModel.id))
            .filter(PracticeRecordModel.user_id.in_(student_ids))
            .scalar()
        ) or 0
        correct_all = (
            db.query(func.count(PracticeRecordModel.id))
            .filter(
                PracticeRecordModel.user_id.in_(student_ids),
                PracticeRecordModel.is_correct.is_(True),
            )
            .scalar()
        ) or 0
        overall_accuracy = round(correct_all / total_all * 100, 1) if total_all > 0 else 0.0

    # 近14天趋势
    trend = []
    for i in range(13, -1, -1):
        d = today_val - timedelta(days=i)
        if student_ids:
            pc = (
                db.query(func.count(PracticeRecordModel.id))
                .filter(
                    PracticeRecordModel.user_id.in_(student_ids),
                    func.date(PracticeRecordModel.answered_at) == d,
                )
                .scalar()
            ) or 0
            cc = (
                db.query(func.count(PracticeRecordModel.id))
                .filter(
                    PracticeRecordModel.user_id.in_(student_ids),
                    func.date(PracticeRecordModel.answered_at) == d,
                    PracticeRecordModel.is_correct.is_(True),
                )
                .scalar()
            ) or 0
            sc = (
                db.query(func.count(SpeakingRecordModel.id))
                .filter(
                    SpeakingRecordModel.user_id.in_(student_ids),
                    func.date(SpeakingRecordModel.created_at) == d,
                )
                .scalar()
            ) or 0
            cr = round(cc / pc * 100, 1) if pc > 0 else 0.0
            # 口语均分
            as_score = 0.0
            speaking_recs = (
                db.query(SpeakingRecordModel.score_json)
                .filter(
                    SpeakingRecordModel.user_id.in_(student_ids),
                    func.date(SpeakingRecordModel.created_at) == d,
                )
                .all()
            )
            if speaking_recs:
                scores = []
                for (sj,) in speaking_recs:
                    if sj and isinstance(sj, dict):
                        s = sj.get("total_score") or sj.get("总分")
                        if s is not None:
                            scores.append(float(s))
                if scores:
                    as_score = round(sum(scores) / len(scores), 1)
        else:
            pc = cc = sc = 0
            cr = 0.0
            as_score = 0.0

        trend.append({
            "date": d.strftime("%Y-%m-%d"),
            "practice_count": pc,
            "speaking_count": sc,
            "correct_rate": cr,
            "avg_speaking_score": as_score,
        })

    # 等级分布
    level_dist = {"A": 0, "B": 0, "C": 0, "unset": 0}
    if student_ids:
        students = db.query(UserModel).filter(UserModel.id.in_(student_ids)).all()
        for s in students:
            key = s.level if s.level in ("A", "B", "C") else "unset"
            level_dist[key] += 1

    return {
        "total_students": total_students,
        "today_active_students": len(active_student_ids),
        "total_practices_today": today_practice,
        "total_speaking_today": today_speaking,
        "overall_accuracy": overall_accuracy,
        "trend": trend,
        "level_distribution": level_dist,
    }


# ══════════════════════════════════════════════
# 分组增强 CRUD
# ══════════════════════════════════════════════
def get_group_detail(db: Session, group_id: str, teacher_id: str) -> dict | None:
    """获取分组详情：成员列表 + 组内统计。"""
    group = db.query(TeacherGroupModel).filter(
        TeacherGroupModel.id == group_id,
        TeacherGroupModel.teacher_id == teacher_id,
    ).first()
    if not group:
        return None

    members = db.query(UserModel).filter(
        UserModel.role == "student",
        UserModel.group_id == group_id,
    ).all()

    member_list = []
    for m in members:
        practice_total = db.query(func.count(PracticeRecordModel.id)).filter(
            PracticeRecordModel.user_id == m.id,
        ).scalar() or 0
        correct_total = db.query(func.count(PracticeRecordModel.id)).filter(
            PracticeRecordModel.user_id == m.id,
            PracticeRecordModel.is_correct.is_(True),
        ).scalar() or 0
        speaking_total = db.query(func.count(SpeakingRecordModel.id)).filter(
            SpeakingRecordModel.user_id == m.id,
        ).scalar() or 0

        member_list.append({
            "id": str(m.id),
            "username": m.username,
            "level": m.level,
            "total_practices": practice_total,
            "accuracy": round(correct_total / practice_total * 100, 1) if practice_total > 0 else 0.0,
            "speaking_count": speaking_total,
        })

    # 组内统计
    total = len(member_list)
    avg_acc = round(sum(x["accuracy"] for x in member_list) / total, 1) if total > 0 else 0.0

    member_ids = [m.id for m in members]
    avg_speaking = 0.0
    active_14d = 0
    if member_ids:
        speaking_recs = db.query(SpeakingRecordModel.score_json).filter(
            SpeakingRecordModel.user_id.in_(member_ids),
        ).all()
        if speaking_recs:
            scores = []
            for (sj,) in speaking_recs:
                if sj and isinstance(sj, dict):
                    s = sj.get("total_score") or sj.get("总分")
                    if s is not None:
                        scores.append(float(s))
            if scores:
                avg_speaking = round(sum(scores) / len(scores), 1)

        since = beijing_now() - timedelta(days=14)
        active_set = set()
        for (uid,) in db.query(PracticeRecordModel.user_id).filter(
            PracticeRecordModel.user_id.in_(member_ids),
            PracticeRecordModel.answered_at >= since,
        ).distinct().all():
            active_set.add(uid)
        for (uid,) in db.query(SpeakingRecordModel.user_id).filter(
            SpeakingRecordModel.user_id.in_(member_ids),
            SpeakingRecordModel.created_at >= since,
        ).distinct().all():
            active_set.add(uid)
        active_14d = len(active_set)

    level_dist = {"A": 0, "B": 0, "C": 0, "unset": 0}
    for m in members:
        key = m.level if m.level in ("A", "B", "C") else "unset"
        level_dist[key] += 1

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.strftime("%Y-%m-%d %H:%M") if group.created_at else None,
        "members": member_list,
        "stats": {
            "total_students": total,
            "avg_accuracy": avg_acc,
            "avg_speaking_score": avg_speaking,
            "active_14d": active_14d,
            "level_distribution": level_dist,
        },
    }


def delete_teacher_group(db: Session, group_id: str, teacher_id: str) -> bool:
    """删除分组，组成员自动取消分组。"""
    group = db.query(TeacherGroupModel).filter(
        TeacherGroupModel.id == group_id,
        TeacherGroupModel.teacher_id == teacher_id,
    ).first()
    if not group:
        return False
    # 组内学生取消分组
    db.query(UserModel).filter(UserModel.group_id == group_id).update(
        {UserModel.group_id: None}
    )
    db.delete(group)
    db.commit()
    return True


def batch_assign_groups(db: Session, student_ids: list[str], teacher_id: str, group_id: str | None) -> int:
    """批量分配学生到分组。检查学生属于该教师管辖。返回成功分配数。"""
    if group_id is not None:
        group = db.query(TeacherGroupModel).filter(
            TeacherGroupModel.id == group_id,
            TeacherGroupModel.teacher_id == teacher_id,
        ).first()
        if not group:
            return 0

    changed = 0
    for sid in student_ids:
        student = db.query(UserModel).filter(
            UserModel.id == sid,
            UserModel.role == "student",
        ).first()
        if not student:
            continue
        student.group_id = group_id
        changed += 1
    db.commit()
    return changed


def get_groups_comparison(db: Session, teacher_id: str) -> list[dict]:
    """获取所有分组的对比数据。"""
    groups = db.query(TeacherGroupModel).filter(
        TeacherGroupModel.teacher_id == teacher_id,
    ).all()

    result = []
    for g in groups:
        members = db.query(UserModel).filter(
            UserModel.role == "student",
            UserModel.group_id == g.id,
        ).all()
        member_ids = [m.id for m in members]
        count = len(member_ids)

        avg_acc = 0.0
        avg_speaking = 0.0
        active_rate = 0.0

        if member_ids:
            total_p = db.query(func.count(PracticeRecordModel.id)).filter(
                PracticeRecordModel.user_id.in_(member_ids),
            ).scalar() or 0
            correct_p = db.query(func.count(PracticeRecordModel.id)).filter(
                PracticeRecordModel.user_id.in_(member_ids),
                PracticeRecordModel.is_correct.is_(True),
            ).scalar() or 0
            avg_acc = round(correct_p / total_p * 100, 1) if total_p > 0 else 0.0

            speaking_recs = db.query(SpeakingRecordModel.score_json).filter(
                SpeakingRecordModel.user_id.in_(member_ids),
            ).all()
            scores = []
            for (sj,) in speaking_recs:
                if sj and isinstance(sj, dict):
                    s = sj.get("total_score") or sj.get("总分")
                    if s is not None:
                        scores.append(float(s))
            if scores:
                avg_speaking = round(sum(scores) / len(scores), 1)

            since = beijing_now() - timedelta(days=14)
            active_set = set()
            for (uid,) in db.query(PracticeRecordModel.user_id).filter(
                PracticeRecordModel.user_id.in_(member_ids),
                PracticeRecordModel.answered_at >= since,
            ).distinct().all():
                active_set.add(uid)
            for (uid,) in db.query(SpeakingRecordModel.user_id).filter(
                SpeakingRecordModel.user_id.in_(member_ids),
                SpeakingRecordModel.created_at >= since,
            ).distinct().all():
                active_set.add(uid)
            active_rate = round(len(active_set) / count * 100, 1) if count > 0 else 0.0

        result.append({
            "group_id": str(g.id),
            "group_name": g.name,
            "student_count": count,
            "avg_accuracy": avg_acc,
            "avg_speaking_score": avg_speaking,
            "active_rate": active_rate,
        })

    return result


# ══════════════════════════════════════════════
# 通信系统 CRUD
# ══════════════════════════════════════════════
from app.models import AnnouncementModel, MessageModel, TaskModel, TaskProgressModel


def create_announcement_crud(db: Session, teacher_id: str, title: str, content: str,
                             target_type: str = "all", target_group_id: str | None = None,
                             is_pinned: bool = False) -> AnnouncementModel:
    ann = AnnouncementModel(teacher_id=teacher_id, title=title, content=content,
                            target_type=target_type, target_group_id=target_group_id,
                            is_pinned=is_pinned)
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


def get_teacher_announcements(db: Session, teacher_id: str, skip: int = 0, limit: int = 20):
    q = db.query(AnnouncementModel).filter(AnnouncementModel.teacher_id == teacher_id)
    total = q.count()
    items = q.order_by(AnnouncementModel.is_pinned.desc(), AnnouncementModel.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_student_announcements(db: Session, student_id: str, skip: int = 0, limit: int = 20):
    student = db.query(UserModel).filter(UserModel.id == student_id).first()
    group_id = student.group_id if student else None
    q = db.query(AnnouncementModel).filter(
        (AnnouncementModel.target_type == "all") |
        ((AnnouncementModel.target_type == "group") & (AnnouncementModel.target_group_id == group_id))
    )
    total = q.count()
    items = q.order_by(AnnouncementModel.is_pinned.desc(), AnnouncementModel.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def update_announcement_crud(db: Session, ann_id: str, teacher_id: str, **kwargs) -> AnnouncementModel | None:
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == ann_id, AnnouncementModel.teacher_id == teacher_id).first()
    if not ann:
        return None
    for k, v in kwargs.items():
        if hasattr(ann, k):
            setattr(ann, k, v)
    db.commit()
    db.refresh(ann)
    return ann


def delete_announcement_crud(db: Session, ann_id: str, teacher_id: str) -> bool:
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == ann_id, AnnouncementModel.teacher_id == teacher_id).first()
    if not ann:
        return False
    db.delete(ann)
    db.commit()
    return True


def send_message_crud(db: Session, sender_id: str, content: str, receiver_id: str | None = None,
                      group_id: str | None = None, subject: str | None = None,
                      parent_id: str | None = None) -> MessageModel:
    msg = MessageModel(sender_id=sender_id, receiver_id=receiver_id, group_id=group_id,
                       subject=subject, content=content, parent_id=parent_id)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_received_messages(db: Session, user_id: str, skip: int = 0, limit: int = 30):
    group_ids_query = db.query(UserModel.group_id).filter(UserModel.id == user_id, UserModel.group_id.isnot(None)).scalar()
    conditions = [MessageModel.receiver_id == user_id]
    if group_ids_query:
        conditions.append(
            (MessageModel.group_id == group_ids_query) & (MessageModel.receiver_id.is_(None))
        )
    from sqlalchemy import or_
    q = db.query(MessageModel).filter(or_(*conditions))
    total = q.count()
    items = q.order_by(MessageModel.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_sent_messages(db: Session, user_id: str, skip: int = 0, limit: int = 30):
    q = db.query(MessageModel).filter(MessageModel.sender_id == user_id)
    total = q.count()
    items = q.order_by(MessageModel.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def mark_message_read(db: Session, msg_id: str) -> bool:
    msg = db.query(MessageModel).filter(MessageModel.id == msg_id).first()
    if not msg:
        return False
    msg.is_read = True
    db.commit()
    return True


def create_task_crud(db: Session, teacher_id: str, title: str, **kwargs) -> TaskModel:
    task = TaskModel(teacher_id=teacher_id, title=title, **kwargs)
    db.add(task)
    db.commit()
    db.refresh(task)
    student_ids = _task_student_ids(db, task)
    for sid in student_ids:
        tp = TaskProgressModel(task_id=task.id, student_id=sid)
        db.add(tp)
    db.commit()
    return task


def _task_student_ids(db: Session, task: TaskModel) -> list[str]:
    q = db.query(UserModel.id).filter(UserModel.role == "student")
    if task.target_type == "group" and task.target_group_id:
        q = q.filter(UserModel.group_id == task.target_group_id)
    return [u[0] for u in q.all()]


def get_teacher_tasks(db: Session, teacher_id: str, group_id: str | None = None,
                      status: str | None = None, skip: int = 0, limit: int = 20):
    q = db.query(TaskModel).filter(TaskModel.teacher_id == teacher_id)
    if group_id:
        q = q.filter(TaskModel.target_group_id == group_id)
    if status:
        q = q.filter(TaskModel.status == status)
    total = q.count()
    items = q.order_by(TaskModel.created_at.desc()).offset(skip).limit(limit).all()
    result = []
    for t in items:
        completed = db.query(func.count(TaskProgressModel.id)).filter(
            TaskProgressModel.task_id == t.id, TaskProgressModel.is_completed.is_(True)
        ).scalar() or 0
        total_count = db.query(func.count(TaskProgressModel.id)).filter(
            TaskProgressModel.task_id == t.id
        ).scalar() or 0
        result.append({
            "id": str(t.id), "teacher_id": str(t.teacher_id), "title": t.title,
            "description": t.description, "target_type": t.target_type,
            "target_group_id": t.target_group_id,
            "practice_goal": t.practice_goal, "speaking_goal": t.speaking_goal,
            "free_talk_goal": t.free_talk_goal, "clip_goal": t.clip_goal,
            "accuracy_goal": t.accuracy_goal,
            "deadline": t.deadline.strftime("%Y-%m-%d") if t.deadline else None,
            "status": t.status,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else None,
            "completed_count": completed, "total_count": total_count,
        })
    return result, total


def update_task_crud(db: Session, task_id: str, teacher_id: str, **kwargs) -> TaskModel | None:
    task = db.query(TaskModel).filter(TaskModel.id == task_id, TaskModel.teacher_id == teacher_id).first()
    if not task:
        return None
    for k, v in kwargs.items():
        if hasattr(task, k):
            setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


def delete_task_crud(db: Session, task_id: str, teacher_id: str) -> bool:
    task = db.query(TaskModel).filter(TaskModel.id == task_id, TaskModel.teacher_id == teacher_id).first()
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True


def get_student_tasks(db: Session, student_id: str):
    progresses = db.query(TaskProgressModel).filter(TaskProgressModel.student_id == student_id).all()
    result = []
    for p in progresses:
        task = db.query(TaskModel).filter(TaskModel.id == p.task_id).first()
        if not task:
            continue
        result.append({
            "id": str(task.id), "title": task.title, "description": task.description,
            "practice_goal": task.practice_goal, "speaking_goal": task.speaking_goal,
            "free_talk_goal": task.free_talk_goal, "clip_goal": task.clip_goal,
            "accuracy_goal": task.accuracy_goal,
            "deadline": task.deadline.strftime("%Y-%m-%d") if task.deadline else None,
            "status": task.status,
            "practice_done": p.practice_done, "speaking_done": p.speaking_done,
            "free_talk_done": p.free_talk_done, "clips_done": p.clips_done,
            "is_completed": p.is_completed,
        })
    return result


def get_task_detail(db: Session, task_id: str, teacher_id: str) -> dict | None:
    """获取任务详情——含每个学生的进度列表。"""
    task = db.query(TaskModel).filter(TaskModel.id == task_id, TaskModel.teacher_id == teacher_id).first()
    if not task:
        return None

    progress_records = db.query(TaskProgressModel).filter(TaskProgressModel.task_id == task_id).all()
    progress_list = []
    for p in progress_records:
        student = db.query(UserModel).filter(UserModel.id == p.student_id).first()
        progress_list.append({
            "student_id": str(p.student_id),
            "student_name": student.username if student else "",
            "practice_done": p.practice_done,
            "speaking_done": p.speaking_done,
            "free_talk_done": p.free_talk_done,
            "clips_done": p.clips_done,
            "current_accuracy": p.current_accuracy,
            "is_completed": p.is_completed,
            "completed_at": p.completed_at.strftime("%Y-%m-%d %H:%M") if p.completed_at else None,
        })

    completed = sum(1 for p in progress_list if p["is_completed"])
    return {
        "id": str(task.id), "teacher_id": str(task.teacher_id), "title": task.title,
        "description": task.description, "target_type": task.target_type,
        "target_group_id": task.target_group_id,
        "practice_goal": task.practice_goal, "speaking_goal": task.speaking_goal,
        "free_talk_goal": task.free_talk_goal, "clip_goal": task.clip_goal,
        "accuracy_goal": task.accuracy_goal,
        "deadline": task.deadline.strftime("%Y-%m-%d") if task.deadline else None,
        "status": task.status,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else None,
        "completed_count": completed, "total_count": len(progress_list),
        "progress": progress_list,
    }


def update_task_progress_for_student(db: Session, student_id: str):
    """学生完成练习后，更新其所有活跃任务的进度快照。"""
    progresses = db.query(TaskProgressModel).join(
        TaskModel, TaskProgressModel.task_id == TaskModel.id
    ).filter(
        TaskProgressModel.student_id == student_id,
        TaskModel.status == "active",
    ).all()

    for p in progresses:
        p.practice_done = db.query(func.count(PracticeRecordModel.id)).filter(
            PracticeRecordModel.user_id == student_id,
        ).scalar() or 0

        p.speaking_done = db.query(func.count(SpeakingRecordModel.id)).filter(
            SpeakingRecordModel.user_id == student_id,
        ).scalar() or 0

        p.free_talk_done = db.query(func.count(FreeConversationModel.id)).filter(
            FreeConversationModel.user_id == student_id,
            FreeConversationModel.status == "completed",
        ).scalar() or 0

        practiced_clips = set()
        for (cid,) in db.query(QuestionModel.clip_id).join(
            PracticeRecordModel, PracticeRecordModel.question_id == QuestionModel.id
        ).filter(
            PracticeRecordModel.user_id == student_id,
        ).distinct().all():
            practiced_clips.add(cid)
        p.clips_done = len(practiced_clips)

        total_all = db.query(func.count(PracticeRecordModel.id)).filter(
            PracticeRecordModel.user_id == student_id,
        ).scalar() or 0
        correct_all = db.query(func.count(PracticeRecordModel.id)).filter(
            PracticeRecordModel.user_id == student_id,
            PracticeRecordModel.is_correct.is_(True),
        ).scalar() or 0
        p.current_accuracy = round(correct_all / total_all * 100, 1) if total_all > 0 else 0.0

        task = p.task_id and db.query(TaskModel).filter(TaskModel.id == p.task_id).first()
        if task:
            if (p.practice_done >= task.practice_goal and
                p.speaking_done >= task.speaking_goal and
                p.free_talk_done >= task.free_talk_goal and
                p.clips_done >= task.clip_goal):
                if not p.is_completed:
                    p.is_completed = True
                    p.completed_at = beijing_now()

    db.commit()


# ── Vocabulary CRUD ──

def add_vocabulary(db: Session, user_id: str, word: str, definition: str = "", clip_id: str | None = None) -> UserVocabularyModel:
    existing = db.query(UserVocabularyModel).filter(
        UserVocabularyModel.user_id == user_id,
        UserVocabularyModel.word == word,
    ).first()
    if existing:
        if definition:
            existing.definition = definition
        if clip_id:
            existing.clip_id = clip_id
        db.commit()
        return existing
    v = UserVocabularyModel(user_id=user_id, word=word, definition=definition, clip_id=clip_id)
    db.add(v)
    db.commit()
    return v


def remove_vocabulary(db: Session, user_id: str, vocab_id: str) -> bool:
    v = db.query(UserVocabularyModel).filter(
        UserVocabularyModel.id == vocab_id,
        UserVocabularyModel.user_id == user_id,
    ).first()
    if not v:
        return False
    db.delete(v)
    db.commit()
    return True


def list_vocabulary(db: Session, user_id: str, page: int = 1, page_size: int = 50, sort: str = "newest") -> tuple[list[UserVocabularyModel], int]:
    q = db.query(UserVocabularyModel).filter(UserVocabularyModel.user_id == user_id)
    total = q.count()
    if sort == "alphabet":
        q = q.order_by(UserVocabularyModel.word.asc())
    elif sort == "mastered":
        q = q.order_by(UserVocabularyModel.mastered.asc(), UserVocabularyModel.created_at.desc())
    else:
        q = q.order_by(UserVocabularyModel.created_at.desc())
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def toggle_vocabulary_mastered(db: Session, user_id: str, vocab_id: str) -> UserVocabularyModel | None:
    v = db.query(UserVocabularyModel).filter(
        UserVocabularyModel.id == vocab_id,
        UserVocabularyModel.user_id == user_id,
    ).first()
    if not v:
        return None
    v.mastered = not v.mastered
    db.commit()
    return v


def lookup_word_definition(db: Session, word: str) -> str | None:
    existing = db.query(UserVocabularyModel.definition).filter(
        UserVocabularyModel.word == word,
        UserVocabularyModel.definition.isnot(None),
        UserVocabularyModel.definition != "",
    ).first()
    return existing[0] if existing else None
