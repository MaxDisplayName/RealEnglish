import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const items = [
  {
    startFrame: 0, svgSrc: "/svgs/undraw_home-cinema_jdm1.svg", svgWidth: 220,
    title: "用真实影视\n学地道英语",
    subtitle: "AI 驱动的英语视听说学习平台",
    tags: ["✨ AI + 真实影视"],
    features: [
      { icon: "🎬", label: "35 段精选美剧 / 英剧 / 电影真实片段" },
      { icon: "🧠", label: "DeepSeek 大模型智能出题" },
      { icon: "🎤", label: "科大讯飞语音评测引擎" },
    ],
  },
  {
    startFrame: 90, svgSrc: "/svgs/around-the-world.svg", svgWidth: 200,
    title: "四大核心能力",
    subtitle: "看 → 听 → 说 → 评，四步闭环提升英语听说",
    tags: ["核心功能"],
    features: [
      { icon: "📺", label: "影视片段学习 — B站播放器内嵌，中英对照" },
      { icon: "🤖", label: "AI 智能出题 — 托业/四六级风格自动生成" },
      { icon: "🎙️", label: "口语评测 — 讯飞 ISE 三维度精准打分" },
      { icon: "📊", label: "学情分析 — 多智能体报告 + 趋势追踪" },
    ],
  },
  {
    startFrame: 180, svgSrc: "/svgs/undraw_progress-data_gvcq.svg", svgWidth: 200,
    title: "学习的每一步\n都算数",
    subtitle: "全方位数据追踪你的英语成长轨迹",
    tags: ["数据追踪"],
    features: [
      { icon: "📚", label: "35 段影视学习片段" },
      { icon: "📏", label: "A / B / C 三级难度分级" },
      { icon: "📐", label: "准确度 · 流畅度 · 完整度 · 总分 四维评分" },
      { icon: "🏷️", label: "7 大内容分类（动画/家庭/社交/演讲/职场/餐饮/日常）" },
    ],
  },
];

export const Scene01Landing: React.FC = () => {
  return (
    <SceneLayout videoSide="left"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part1.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 440 }}><TextCycle items={items} /></div>}
    />
  );
};
