import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const items = [
  {
    startFrame: 0, svgSrc: "/svgs/woman-with-headphone.svg", svgWidth: 200,
    title: "跟读模式",
    subtitle: "播放原声 → 用户录音 → 讯飞语音评测，逐句纠音",
    tags: ["跟读评测"],
    features: [
      { icon: "🔊", label: "播放原声音频，逐句跟读模仿" },
      { icon: "🎙️", label: "MediaRecorder 录音，WebM/Opus 编码" },
      { icon: "📏", label: "讯飞 ISE 引擎评测：准确度 · 流畅度 · 完整度 · 总分" },
      { icon: "⭐", label: "5 分制评分 + AI 激励性反馈" },
    ],
  },
  {
    startFrame: 210, svgSrc: "/svgs/undraw_voice-interface_vo02.svg", svgWidth: 200,
    title: "自由应答模式",
    subtitle: "AI 生成开放性问题，用户口述回答，即时评分",
    tags: ["自由应答"],
    features: [
      { icon: "💡", label: "DeepSeek 根据片段内容生成开放性问题" },
      { icon: "🗣️", label: "用户口述英文回答，语音转文字评测" },
      { icon: "⚡", label: "即时评分 + 语法词汇纠正反馈" },
    ],
  },
  {
    startFrame: 450, svgSrc: "/svgs/undraw_casual-chat_4byz.svg", svgWidth: 220,
    title: "情景式\n自由对话",
    subtitle: "AI 生成真实生活场景和角色，多轮英语互动对话",
    tags: ["情景对话"],
    features: [
      { icon: "🎭", label: "AI 自动生成场景（如「咖啡店点单」「机场值机」）" },
      { icon: "👥", label: "用户选择/扮演角色与 AI 多轮对话" },
      { icon: "⌨️", label: "支持文字输入 + 语音输入双模式" },
    ],
  },
  {
    startFrame: 750, svgSrc: "/svgs/undraw_public-speaking_m17t.svg", svgWidth: 220,
    title: "四维度\n综合评测",
    subtitle: "对话结束后从四个维度统一评测，讯飞 ISE 引擎驱动",
    tags: ["综合评测"],
    features: [
      { icon: "✅", label: "参与完成度 — 对话覆盖度评估" },
      { icon: "📝", label: "语法 — 句法准确性打分" },
      { icon: "📚", label: "词汇 — 用词丰富度评估" },
      { icon: "💬", label: "流畅度 — 表达连贯性评分" },
    ],
  },
];

export const Scene05Speaking: React.FC = () => {
  return (
    <SceneLayout videoSide="left"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part5.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 460 }}><TextCycle items={items} /></div>}
    />
  );
};
