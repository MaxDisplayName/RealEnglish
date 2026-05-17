import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const items = [
  {
    startFrame: 0, svgSrc: "/svgs/movie-night.svg", svgWidth: 200,
    title: "丰富的影视\n片段库",
    subtitle: "7 大内容分类，A/B/C 三级难度，卡片网格展示",
    tags: ["片段库"],
    features: [
      { icon: "🎞️", label: "7 大分类：动画/家庭/社交/演讲/职场/餐饮/日常" },
      { icon: "📊", label: "A / B / C 三级难度一键筛选" },
      { icon: "🔍", label: "卡片网格 + 分类/难度双重过滤" },
    ],
  },
  {
    startFrame: 120, svgSrc: "/svgs/undraw_online-video_ecqg.svg", svgWidth: 220,
    title: "沉浸式\n片段学习",
    subtitle: "B 站播放器内嵌，支持起始时间跳转，中英对照字幕",
    tags: ["视频学习"],
    features: [
      { icon: "▶️", label: "B 站 iframe 播放器嵌入" },
      { icon: "⏱️", label: "起始/结束时间精确控制" },
      { icon: "🌐", label: "英文原文 + 中文翻译一键切换" },
    ],
  },
  {
    startFrame: 300, svgSrc: "/svgs/undraw_file-search_cbur.svg", svgWidth: 200,
    title: "智能翻译\n与查词",
    subtitle: "流式大模型翻译，点击单词弹出 DeepSeek 释义卡片",
    tags: ["翻译查词"],
    features: [
      { icon: "🔄", label: "SSE 流式大模型翻译，逐字输出" },
      { icon: "📖", label: "点击对话中任意英文单词查词" },
      { icon: "💾", label: "一键收藏到个人单词本" },
    ],
  },
  {
    startFrame: 480, svgSrc: "/svgs/chat-bot.svg", svgWidth: 180,
    title: "片段学习助手",
    subtitle: "可拖动悬浮 AI 助手，解答词汇/语法/文化背景问题",
    tags: ["AI 助手"],
    features: [
      { icon: "🤖", label: "右下角悬浮气泡，可拖动到任意位置" },
      { icon: "💬", label: "针对当前片段内容智能解答" },
      { icon: "📚", label: "词汇释义 · 语法分析 · 文化背景" },
    ],
  },
];

export const Scene03Clips: React.FC = () => {
  return (
    <SceneLayout videoSide="left" glowColor="rgba(206,130,255,0.06)"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part3.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 440 }}><TextCycle items={items} /></div>}
    />
  );
};
