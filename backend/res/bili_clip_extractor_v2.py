#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频片段处理工具 v2（集成 DeepSeek 角色标注 + 性别识别 + 剧情总结）

改进（相比 v1）：
- 操作 CSV 文件（backend/res/video_clips.csv）而非 xlsx
- 支持 Upsert：同一片段（BV号+分P+起始时间）存在则更新，不存在则追加
- 去掉"备注"列，新增"角色性别"列（AI 自动识别）
- 自动从 ../.env 读取 OPENAI_API_KEY，与后端统一
- 纯 Whisper 语音识别（不再使用官方字幕）
- 分类选择器：列出已有类别，可选已有或新建
- AI 审核循环：生成后需用户确认，不满意可输入修改意见重新生成
- 每次保存自动按难度排序

用法：
  交互模式：python bili_clip_extractor_v2.py
  命令行模式：python bili_clip_extractor_v2.py --bvid BVxxx --start 32 --end 67 --title "Modern Family" --category "家庭生活" --difficulty A
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------- 配置 ----------
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_FILE = SCRIPT_DIR / "video_clips.csv"
ENV_FILE = SCRIPT_DIR.parent / ".env"

API_URL = "https://api.deepseek.com/v1/chat/completions"


def _load_api_key() -> str:
    """加载 API Key：优先 .env 文件 → 环境变量 → 用户输入"""
    # 1. 尝试从 ../.env 读取 OPENAI_API_KEY
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    # 2. 环境变量
    for var in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        val = os.environ.get(var)
        if val:
            return val
    # 3. 用户输入
    key = input("请输入 DeepSeek API Key: ").strip()
    if key:
        return key
    print("错误：未提供 API Key。")
    sys.exit(1)


API_KEY = _load_api_key()

# ---------- API 调用 ----------

def call_deepseek(show_name: str, raw_dialogue: str, context: str = "") -> dict:
    """
    调用 DeepSeek API 对对话文本进行角色标注、性别识别和剧情总结。
    返回 {"marked_dialogue": str, "summary": str, "character_genders": dict}
    """
    context_section = ""
    if context:
        context_section = f"""
【补充背景信息（由用户提供）】：
{context}

请优先使用上述信息来推断说话人角色名和性别。"""

    prompt = f"""你是英语影视剧分析专家。以下是《{show_name}》中的一段对话（语音转文本提取），目前没有标注说话人。{context_section}

请完成三项任务：
1. 为每句话标注说话人标签。能推断具体角色名则用 [角色名]，否则用 [Man]/[Woman]/[Boy]/[Girl] 等通用标签。
2. 用简洁中文总结核心剧情（不超过60字）。
3. 推断每个说话人的性别（male/female），返回角色名→性别的映射。

保持原英文单词不变，不要翻译。如发现明显的语音识别错误请顺便纠正。

返回严格 JSON 格式：
{{
  "marked_dialogue": "标注后的完整对话文本，每行以 [标签] 开头",
  "summary": "剧情总结",
  "character_genders": {{"角色名": "male", "角色名": "female"}}
}}

原始对话：
{raw_dialogue}"""

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = __import__("requests").post(API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        data = json.loads(content)
        return {
            "marked_dialogue": data.get("marked_dialogue", raw_dialogue),
            "summary": data.get("summary", ""),
            "character_genders": data.get("character_genders", {}),
        }
    except Exception as e:
        print(f"  DeepSeek API 调用失败: {e}")
        return {"marked_dialogue": raw_dialogue, "summary": "", "character_genders": {}}


# ---------- 时间解析 ----------

def parse_time(time_str: str) -> int:
    """将时间字符串转为秒数（支持 秒数 / mm:ss / hh:mm:ss）"""
    time_str = time_str.strip()
    if not time_str:
        raise ValueError("时间不能为空")
    if re.match(r"^\d+(\.\d+)?$", time_str):
        return int(float(time_str))
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    raise ValueError(f"无法解析的时间格式: {time_str}")


# ---------- iframe URL ----------

def generate_iframe_url(bv: str, page: int, start_sec: int) -> str:
    return f"https://player.bilibili.com/player.html?bvid={bv}&page={page}&t={start_sec}"


# ---------- 音频处理（纯 Whisper） ----------

def download_audio_segment(bv: str, page: int, start_sec: int, end_sec: int, output_dir: str) -> str | None:
    """使用 yt-dlp 下载音频片段（Whisper 备用）"""
    url = f"https://www.bilibili.com/video/{bv}?p={page}"
    output_template = os.path.join(output_dir, f"{bv}_p{page}_segment")
    cmd = [
        "py", "-m", "yt_dlp",
        "--download-sections", f"*{start_sec}-{end_sec}",
        "--force-keyframes-at-cuts",
        "--extract-audio", "--audio-format", "mp3",
        "-o", output_template + ".%(ext)s", url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return None
    for f in os.listdir(output_dir):
        if f.startswith(os.path.basename(output_template)) and f.endswith(".mp3"):
            return os.path.join(output_dir, f)
    return None


def transcribe_audio_with_whisper(audio_path: str) -> str:
    """使用 Whisper 转写音频"""
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="en")
    return result["text"].strip()


# ---------- CSV 操作 ----------

def read_csv() -> list[dict]:
    """读取 CSV，返回行列表。若文件不存在返回空列表。"""
    if not CSV_FILE.exists():
        return []
    with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict]):
    """写入 CSV，按难度排序。"""
    fieldnames = [
        "BV号", "分P", "起始时间(秒)", "结束时间(秒)", "iframe链接",
        "剧集名称", "对话类别", "难度", "对话文本", "字幕来源", "片段剧情描述", "角色性别",
    ]
    # 按难度排序
    diff_order = {"A": 0, "B": 1, "C": 2}
    rows.sort(key=lambda r: diff_order.get(r.get("难度", ""), 99))

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def find_existing(rows: list[dict], bv: str, page: int, start_sec: int) -> tuple[int, dict | None]:
    """在行列表中查找匹配的片段，返回 (索引, 行) 或 (-1, None)"""
    for i, row in enumerate(rows):
        if row.get("BV号") == bv and int(row.get("分P", 0)) == page and int(row.get("起始时间(秒)", 0)) == start_sec:
            return i, row
    return -1, None


def upsert_clip(clip_data: dict):
    """将片段数据写入 CSV（存在则更新，不存在则追加）"""
    rows = read_csv()
    idx, existing = find_existing(rows, clip_data["BV号"], clip_data["分P"], clip_data["起始时间(秒)"])

    if existing:
        rows[idx] = clip_data
        print(f"  已更新现有片段: {clip_data['剧集名称']} ({clip_data['难度']}级)")
    else:
        rows.append(clip_data)
        print(f"  已新增片段: {clip_data['剧集名称']} ({clip_data['难度']}级)")

    write_csv(rows)
    print(f"  CSV 保存完成，共 {len(rows)} 条记录")


# ---------- 单条片段处理 ----------

def process_one_clip(bv: str, page: int, start_sec: int, end_sec: int,
                     show_name: str, category: str, difficulty: str,
                     extra_context: str = "") -> dict | None:
    """处理一个片段：下载音频 → Whisper → AI加工 → 审核 → 保存。返回 clip_data 或 None。"""
    work_dir = tempfile.mkdtemp(prefix="bili_extract_")
    print(f"  临时目录: {work_dir}")

    try:
        # 1. Whisper 语音识别
        print("  [1/3] 下载音频 + Whisper 转写...")
        audio_file = download_audio_segment(bv, page, start_sec, end_sec, work_dir)
        if not audio_file:
            print("    错误：音频下载失败，请检查网络或 BV 号")
            return None

        raw_dialogue = transcribe_audio_with_whisper(audio_file)
        if not raw_dialogue.strip():
            print("    错误：Whisper 未识别到任何语音内容")
            return None
        print(f"    Whisper 转写完成 ({len(raw_dialogue)} 字符)")
        print(f"    原文预览: {raw_dialogue[:120]}...")

        # 2. AI 加工 + 审核循环
        print("  [2/3] AI 角色标注 + 性别识别 + 剧情总结...")
        context = extra_context
        while True:
            result = call_deepseek(show_name, raw_dialogue, context)
            marked = result["marked_dialogue"]
            summary = result["summary"]
            genders = result.get("character_genders", {})

            # 展示 AI 结果供用户审核
            print("\n  " + "─" * 45)
            print("  【AI 生成的标注对话】")
            print("  " + marked.replace("\n", "\n  "))
            print(f"\n  【剧情总结】{summary}")
            if genders:
                print(f"  【角色性别】{json.dumps(genders, ensure_ascii=False)}")
            print("  " + "─" * 45)

            choice = input("\n  确认保存？(Y=保存 / N=重新生成 / Q=放弃): ").strip().upper()
            if choice == "Y":
                break
            elif choice == "Q":
                print("  已放弃本条片段。")
                return None
            else:
                # 重新生成：收集新的提示词
                new_hint = input("  请输入修改意见（如'角色标注有误，说话人是Jay和Gloria'）: ").strip()
                context = (extra_context + "\n【用户修改意见】" + new_hint).strip()
                print("  正在重新生成...")

        # 3. 构建数据
        print("  [3/3] 保存到 CSV...")
        clip_data = {
            "BV号": bv,
            "分P": str(page),
            "起始时间(秒)": str(start_sec),
            "结束时间(秒)": str(end_sec),
            "iframe链接": generate_iframe_url(bv, page, start_sec),
            "剧集名称": show_name,
            "对话类别": category,
            "难度": difficulty,
            "对话文本": marked,
            "字幕来源": "Whisper (AI)",
            "片段剧情描述": summary,
            "角色性别": json.dumps(genders, ensure_ascii=False) if genders else "",
        }
        return clip_data

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        print("  临时文件已清理")


# ---------- 分类辅助 ----------

def get_existing_categories() -> list[str]:
    """从 CSV 中提取所有已有的对话类别（去重排序）"""
    rows = read_csv()
    cats = sorted(set(r.get("对话类别", "").strip() for r in rows if r.get("对话类别", "").strip()))
    return cats


def prompt_category() -> str:
    """让用户选择已有分类或输入新分类"""
    existing = get_existing_categories()
    if existing:
        print("\n  当前已有的对话类别：")
        for i, cat in enumerate(existing, 1):
            print(f"    {i}. {cat}")
        print(f"    {len(existing) + 1}. [输入新类别]")
        choice = input(f"  请选择 (1-{len(existing) + 1}，直接回车选第1项): ").strip()
        if choice and choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(existing):
                return existing[idx - 1]
        return input("  请输入新类别名称: ").strip()
    else:
        return input("  对话类别 (如 家庭生活、动画、职场): ").strip()


# ---------- 交互主循环 ----------

def interactive_mode():
    """交互式录入片段"""
    print("=" * 55)
    print("  B站视频片段处理工具 v2")
    print("  CSV 路径:", str(CSV_FILE))
    print("  API Key :", API_KEY[:12] + "..." if len(API_KEY) > 12 else "未设置")
    print("=" * 55)

    if not API_KEY:
        print("错误：未找到 API Key，请检查 .env 或环境变量。")
        sys.exit(1)

    while True:
        print("\n--- 新片段录入 (直接回车退出) ---")
        bv = input("BV 号: ").strip()
        if not bv:
            print("已退出。")
            break

        page_str = input("分P编号 (默认1): ").strip()
        page = int(page_str) if page_str else 1

        try:
            start_sec = parse_time(input("起始时间 (秒数或 mm:ss): ").strip())
            end_sec = parse_time(input("结束时间 (秒数或 mm:ss): ").strip())
        except ValueError as e:
            print(f"时间解析错误: {e}")
            continue

        if start_sec >= end_sec:
            print("错误：起始时间必须小于结束时间")
            continue

        show_name = input("剧集/影片名称: ").strip()
        category = prompt_category()
        difficulty = input("难度 (A/B/C): ").strip().upper()
        if difficulty not in ("A", "B", "C"):
            print("难度必须为 A, B 或 C")
            continue

        extra_context = ""
        if input("补充背景信息以提高 AI 准确度？(Y/N): ").strip().upper() == "Y":
            extra_context = input("背景信息 (如 对话者是Jay和Gloria): ").strip()

        print()
        clip_data = process_one_clip(bv, page, start_sec, end_sec, show_name, category, difficulty, extra_context)
        if clip_data:
            upsert_clip(clip_data)
        print("=" * 55)


# ---------- 命令行入口 ----------

def cli_mode():
    """命令行模式，用于脚本批量调用"""
    import argparse
    parser = argparse.ArgumentParser(description="B站视频片段处理工具 v2")
    parser.add_argument("--bvid", required=True, help="BV号")
    parser.add_argument("--page", type=int, default=1, help="分P编号")
    parser.add_argument("--start", type=str, required=True, help="起始时间 (秒数或 mm:ss)")
    parser.add_argument("--end", type=str, required=True, help="结束时间")
    parser.add_argument("--title", required=True, help="剧集名称")
    parser.add_argument("--category", required=True, help="对话类别")
    parser.add_argument("--difficulty", required=True, choices=["A", "B", "C"], help="难度")
    parser.add_argument("--context", default="", help="背景信息")
    args = parser.parse_args()

    start_sec = parse_time(args.start)
    end_sec = parse_time(args.end)

    clip_data = process_one_clip(args.bvid, args.page, start_sec, end_sec,
                                 args.title, args.category, args.difficulty, args.context)
    if clip_data:
        upsert_clip(clip_data)
    else:
        print("处理失败")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_mode()
    else:
        interactive_mode()
