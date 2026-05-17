"""初始化数据库——删除旧库，创建测试用户、分组和模拟练习数据。"""
import sys, os, random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(__file__))

db_path = os.path.join(os.path.dirname(__file__), "reelenglish.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print("旧数据库已删除")

from app.db import engine, SessionLocal
from app.models import (UserModel, TeacherGroupModel, UserVocabularyModel, Base,
                         QuestionModel, PracticeRecordModel, SpeakingRecordModel,
                         TaskModel, TaskProgressModel, AnnouncementModel,
                         FreeConversationModel, ConversationMessageModel,
                         AssistantThreadModel, ThreadMessageModel)
from app.utils import hash_password
from app.time_utils import beijing_now

Base.metadata.create_all(bind=engine)
print("数据库表已创建")

db = SessionLocal()

# CSV 同步 + 题目
from app.db import sync_clips_from_csv, _seed_fallback_questions
clips = sync_clips_from_csv(db)
if clips: _seed_fallback_questions(db, clips)
print(f"片段 {len(clips)} 个，题目已加载")

# ── 工具函数 ──
def add_teacher(name, email, code):
    u = UserModel(username=name, email=email, role="teacher",
                  hashed_password=hash_password("pass123"), invite_code=code)
    db.add(u); db.flush()
    return u.id

def add_group(teacher_id, name, desc=""):
    g = TeacherGroupModel(teacher_id=teacher_id, name=name, description=desc)
    db.add(g); db.flush()
    return g.id

def add_student(name, email, level, group_id, teacher_id):
    u = UserModel(username=name, email=email, role="student",
                  hashed_password=hash_password("pass123"), level=level, group_id=group_id,
                  teacher_id=teacher_id)
    db.add(u); db.flush()
    return u.id

# ── 教师 ──
tw = add_teacher("teacher_wang", "wang@reelenglish.com", "W4X9")
tl = add_teacher("teacher_li", "li@reelenglish.com", "K2M7")
print(f"教师: teacher_wang, teacher_li")

# ── 分组 ──
g_w1 = add_group(tw, "公选(1)班", "英语基础较好，目标冲刺高考高分")
g_w2 = add_group(tw, "公选(2)班", "需要加强听力和口语训练")
g_l1 = add_group(tl, "提高班", "中高级学员，重点提升影视英语理解能力")
g_l2 = add_group(tl, "基础班", "初级学员，建立基础词汇和语感")
print(f"分组: 4 个")

# ── 学生 ──
students_def = [
    ("zhangsan", "zhang@stu.com", "A", g_w1), ("lisi", "li@stu.com", "B", g_w1),
    ("wangwu", "wang@stu.com", "B", g_w1), ("wujiu", "wu@stu.com", "A", g_w1),
    ("zhaoliu", "zhao@stu.com", "C", g_w2), ("sunqi", "sun@stu.com", "C", g_w2),
    ("zhouba", "zhou@stu.com", "B", g_w2),
    ("xiaoming", "xm@stu.com", "A", g_l1), ("xiaohong", "xh@stu.com", "A", g_l1),
    ("xiaogang", "xg@stu.com", "B", g_l1),
    ("xiaoli", "xl@stu.com", "C", g_l2), ("xiaowei", "xw@stu.com", "C", g_l2),
]
# teacher_id 映射：w1,w2 → tw, l1,l2 → tl
teacher_id_map = {g_w1: tw, g_w2: tw, g_l1: tl, g_l2: tl}

student_map = {}
for name, email, level, gid in students_def:
    sid = add_student(name, email, level, gid, teacher_id_map[gid])
    student_map[name] = {"id": sid, "level": level, "group_id": gid}
print(f"学生: {len(students_def)} 名")

# ── 练习记录 ──
all_questions = db.query(QuestionModel).all()
qids = [q.id for q in all_questions]
now = beijing_now()
p_total = 0

for name, info in student_map.items():
    lv = info["level"]
    if lv == "A": cr, n = random.uniform(0.72, 0.90), random.randint(25, 40)
    elif lv == "B": cr, n = random.uniform(0.58, 0.78), random.randint(18, 32)
    else: cr, n = random.uniform(0.42, 0.62), random.randint(12, 25)
    for _ in range(n):
        db.add(PracticeRecordModel(
            user_id=info["id"], question_id=random.choice(qids),
            is_correct=random.random() < cr,
            answered_at=now - timedelta(days=random.randint(0, 13), hours=random.randint(0, 23), minutes=random.randint(0, 59)),
        ))
        p_total += 1
print(f"练习: {p_total} 条")

# ── 口语记录 ──
clip_ids = [c[0] for c in db.query(QuestionModel.clip_id).distinct().all()]
s_total = 0
for name, info in student_map.items():
    lv = info["level"]
    if lv == "A": n, sr = random.randint(8, 15), (3.5, 4.8)
    elif lv == "B": n, sr = random.randint(4, 10), (2.5, 4.0)
    else: n, sr = random.randint(1, 6), (1.5, 3.0)
    for _ in range(n):
        sc = round(random.uniform(*sr), 1)
        db.add(SpeakingRecordModel(
            user_id=info["id"], clip_id=random.choice(clip_ids) if clip_ids else None,
            mode=random.choice(["repeat","shadow","free"]),
            reference_text="Sample speaking reference text.",
            score_json={"total_score": sc, "accuracy": round(sc-0.2,1), "fluency": round(sc-0.1,1), "integrity": sc},
            duration_sec=random.randint(15, 60),
            created_at=now - timedelta(days=random.randint(0, 13), hours=random.randint(0, 23)),
        ))
        s_total += 1
print(f"口语: {s_total} 条")

# ── 任务 ──
task_defs = [
    (tw, g_w1, "每日练习 - 公选(1)班", "20题+8口语+10片段"),
    (tw, g_w2, "每日练习 - 公选(2)班", "15题+5口语+8片段"),
    (tl, g_l1, "影视英语挑战 - 提高班", "25题+10口语+15片段"),
    (tl, g_l2, "基础巩固 - 基础班", "10题+3口语+5片段"),
]
tp_total = 0
for tid, gid, title, desc in task_defs:
    task = TaskModel(teacher_id=tid, title=title, description=desc,
                     target_type="group", target_group_id=gid,
                     practice_goal=20, speaking_goal=8, free_talk_goal=3, clip_goal=10,
                     accuracy_goal=70.0, deadline=now+timedelta(days=7), status="active")
    db.add(task); db.flush()
    for name, info in student_map.items():
        if info["group_id"] == gid:
            db.add(TaskProgressModel(
                task_id=task.id, student_id=info["id"],
                practice_done=random.randint(3, 18), speaking_done=random.randint(1, 7),
                free_talk_done=random.randint(0, 2), clips_done=random.randint(2, 8),
                current_accuracy=round(random.uniform(55, 90), 1),
            ))
            tp_total += 1
print(f"任务: 4 个, 进度: {tp_total} 条")

# ── 公告 ──
for tid, title, content in [
    (tw, "欢迎使用 RealEnglish", "请先完成定级测试，根据推荐等级开始学习。"),
    (tw, "本周听力训练重点", "重点练习听写和听力理解，目标每位同学完成20道听力题。"),
    (tl, "影视英语学习指南", "从感兴趣的影视类别开始，先听再看字幕，最后跟读模仿发音。"),
]:
    db.add(AnnouncementModel(teacher_id=tid, title=title, content=content, target_type="all"))
print(f"公告: 3 条")

db.commit()
db.close()

# ── 导出 ──
cred_path = os.path.join(os.path.dirname(__file__), "..", "test_accounts.txt")
g_map = {g_w1: ("teacher_wang", "高一(1)班"), g_w2: ("teacher_wang", "高一(2)班"),
         g_l1: ("teacher_li", "提高班"), g_l2: ("teacher_li", "基础班")}
lines = ["=" * 50, "RealEnglish 测试账号", "=" * 50, ""]
lines.append("【教师】")
lines.append("teacher_wang  / pass123  邀请码: W4X9  (7名学生)")
lines.append("teacher_li    / pass123  邀请码: K2M7  (5名学生)")
lines.append("")
lines.append("【学生 — A=高级 B=中级 C=初级】")
lines.append(f"{'用户名':<12}{'密码':<10}{'等级':<6}{'教师':<16}{'分组':<12}")
lines.append("-" * 56)
for name, email, lv, gid in students_def:
    t, g = g_map[gid]
    lines.append(f"{name:<12}{'pass123':<10}{lv:<6}{t:<16}{g:<12}")
lines.append(f"\n练习{p_total}条 | 口语{s_total}条 | 任务4个 | 公告3条 | 密码pass123")

with open(cred_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n凭证: {cred_path}")
print("=== 完成 ===")
