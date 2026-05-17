import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const items = [
  {
    startFrame: 0, svgSrc: "/svgs/road-to-knowledge.svg", svgWidth: 200,
    title: "学习数据看板",
    subtitle: "统计卡片 · ECharts 趋势图 · GitHub 风格贡献热力图",
    tags: ["数据看板"],
    features: [
      { icon: "📊", label: "3 统计卡片：今日练习 / 学习片段 / 口语练习" },
      { icon: "📈", label: "ECharts 折线图：每日练习+正确率+口语均分趋势" },
      { icon: "🟩", label: "GitHub 风格 27 周 × 7 天贡献热力图" },
    ],
  },
  {
    startFrame: 120, svgSrc: "/svgs/undraw_business-chat_xea1.svg", svgWidth: 200,
    title: "AI 学情分析",
    subtitle: "Agent 调用 get_my_stats 等工具，分析练习/口语数据，给出改进建议",
    tags: ["Agent 分析"],
    features: [
      { icon: "🔧", label: "调用 get_my_stats 工具获取学习统计" },
      { icon: "📋", label: "综合分析练习次数、正确率、口语评分趋势" },
      { icon: "💡", label: "AI 给出个性化改进建议和薄弱环节提醒" },
    ],
  },
  {
    startFrame: 450, svgSrc: "/svgs/ai-response.svg", svgWidth: 200,
    title: "AI 智能推荐",
    subtitle: "Agent 搜索匹配用户等级的片段，推送带链接的推荐表格",
    tags: ["智能推荐"],
    features: [
      { icon: "🔍", label: "调用 search_clips 工具关键词模糊搜索" },
      { icon: "⭐", label: "按用户难度等级 + 兴趣偏好匹配推荐" },
      { icon: "📊", label: "Markdown 推荐表格 + clip:// 可点击链接" },
    ],
  },
];

export const Scene06Dashboard: React.FC = () => {
  return (
    <SceneLayout videoSide="right" glowColor="rgba(28,176,246,0.06)"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part6.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 440 }}><TextCycle items={items} /></div>}
    />
  );
};
