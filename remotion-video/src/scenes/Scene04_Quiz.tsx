import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const items = [
  {
    startFrame: 0, svgSrc: "/svgs/chat-with-ai.svg", svgWidth: 200,
    title: "AI 智能出题",
    subtitle: "DeepSeek 大模型根据片段对话内容自动生成听力题",
    tags: ["AI 出题"],
    features: [
      { icon: "🧠", label: "DeepSeek 大模型自动生成" },
      { icon: "📋", label: "托业 / 四六级风格 Part2 & Part3" },
      { icon: "🎥", label: "题目关联视频片段播放" },
    ],
  },
  {
    startFrame: 150, svgSrc: "/svgs/undraw_question-answered_ezyn.svg", svgWidth: 200,
    title: "个人单词本",
    subtitle: "查词收藏 · 列表排序 · 掌握状态切换",
    tags: ["单词本"],
    features: [
      { icon: "📖", label: "从对话中查词并一键收藏" },
      { icon: "📑", label: "列表视图 + 排序（时间/字母/掌握度）" },
      { icon: "✅", label: "掌握/未掌握状态标记切换" },
    ],
  },
  {
    startFrame: 360, svgSrc: "/svgs/typing.svg", svgWidth: 200,
    title: "单词检测模式",
    subtitle: "AI 基于个人词库生成填空/选择题，错题自动联动",
    tags: ["检测模式"],
    features: [
      { icon: "✏️", label: "AI 根据个人单词本生成填空/选择题" },
      { icon: "🔄", label: "答错单词自动关联错题本" },
      { icon: "📈", label: "检测结果反馈掌握程度" },
    ],
  },
  {
    startFrame: 510, svgSrc: "/svgs/undraw_notify_drs8.svg", svgWidth: 200,
    title: "错题本",
    subtitle: "答题错误自动收录，支持分类复习与解析对照",
    tags: ["错题本"],
    features: [
      { icon: "📕", label: "练习错误自动收录" },
      { icon: "🔍", label: "分类筛选 + 解析对照复习" },
      { icon: "📊", label: "错题统计追踪薄弱环节" },
    ],
  },
];

export const Scene04Quiz: React.FC = () => {
  return (
    <SceneLayout videoSide="right" glowColor="rgba(255,150,0,0.06)"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part4.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 440 }}><TextCycle items={items} /></div>}
    />
  );
};
