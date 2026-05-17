import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const teacherItems = [
  {
    startFrame: 0, svgSrc: "/svgs/learning.svg", svgWidth: 200,
    title: "教师管理看板",
    subtitle: "4 统计卡片 · ECharts 趋势图 · 等级分布环形图 · 按分组筛选",
    tags: ["管理看板"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "📊", label: "总学生数 / 今日活跃 / 今日练习 / 今日口语 统计卡片" },
      { icon: "📈", label: "ECharts 练习趋势 + 正确率 + 口语均分图" },
      { icon: "🍩", label: "等级分布环形图 + 学习预警条（3类预警）" },
    ],
  },
  {
    startFrame: 90, svgSrc: "/svgs/undraw_work-friends_g4mn.svg", svgWidth: 220,
    title: "学生管理",
    subtitle: "三标签页：学生列表 · 分组管理 · 分级管理，支持搜索和批量操作",
    tags: ["学生管理"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "📋", label: "学生列表 — 分页+搜索，行内等级更新" },
      { icon: "👥", label: "分组管理 — 创建/编辑/解散分组，批量分配学生" },
      { icon: "🏷️", label: "分级管理 — A/B/C 一键批量应用" },
      { icon: "📂", label: "详情抽屉 — 练习统计+口语录音回放+AI报告" },
    ],
  },
  {
    startFrame: 420, svgSrc: "/svgs/undraw_messages_okui.svg", svgWidth: 200,
    title: "师生通信\n与任务公告",
    subtitle: "气泡聊天室（单聊+群发）· 学习任务创建与进度追踪 · 全局公告发布",
    tags: ["通信任务"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "💬", label: "左侧会话列表 + 右侧气泡聊天区" },
      { icon: "📝", label: "学习任务：练习/口语/对话/片段四项指标+截止日期" },
      { icon: "📢", label: "公告管理：发布/置顶/编辑，学生登录弹窗展示" },
    ],
  },
  {
    startFrame: 510, svgSrc: "/svgs/chat.svg", svgWidth: 200,
    title: "Agent：\n学情查询",
    subtitle: "调用 list_my_students 工具，查看全部学生信息与等级分布",
    tags: ["Agent 查学情"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "🔍", label: "list_my_students — 获取全部学生列表" },
      { icon: "📊", label: "返回学生等级分布、活跃状态等信息" },
      { icon: "📋", label: "支持分组筛选查看" },
    ],
  },
  {
    startFrame: 630, svgSrc: "/svgs/undraw_group-chat_4xw0.svg", svgWidth: 220,
    title: "Agent：\n创建任务",
    subtitle: "查看分组情况 → 设计任务 → create_task_tool 创建并自动分配",
    tags: ["Agent 建任务"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "👥", label: "get_group_students_detail — 查看分组学生详情" },
      { icon: "📝", label: "create_task_tool — 创建学习任务" },
      { icon: "🔄", label: "自动为组内学生生成进度快照" },
    ],
  },
  {
    startFrame: 990, svgSrc: "/svgs/ai-chat.svg", svgWidth: 200,
    title: "Agent：\n发布公告",
    subtitle: "调用 send_announcement_tool，向绑定学生推送全局公告",
    tags: ["Agent 发公告"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "📢", label: "send_announcement_tool — 创建并发布公告" },
      { icon: "🔔", label: "绑定学生登录后弹出毛玻璃公告面板" },
      { icon: "✅", label: "学生已读确认后不再显示" },
    ],
  },
  {
    startFrame: 1230, svgSrc: "/svgs/undraw_recording_1q6x.svg", svgWidth: 200,
    title: "Agent：\n进度追踪",
    subtitle: "查看任务完成情况，发送私信提醒未完成学生 — 共 19 个工具",
    tags: ["Agent 追进度"],
    tagColor: "#B45309", tagBgColor: "#FEF3C7",
    features: [
      { icon: "📊", label: "get_task_progress — 查看各任务完成进度" },
      { icon: "💬", label: "send_message — 向未完成学生发送私信提醒" },
      { icon: "🔧", label: "教师 Agent 共 19 个工具，全面覆盖教学管理" },
    ],
  },
];

/**
 * 场景 7 — 教师端展示（46s / 1380f）
 */
export const Scene07Teacher: React.FC = () => {
  return (
    <SceneLayout videoSide="left"
      background="linear-gradient(180deg, #FFF8E1 0%, #FFFDE7 40%, #FFFFFF 100%)"
      glowColor="rgba(255,152,0,0.10)"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part7.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 460 }}><TextCycle items={teacherItems} accentColor="#B45309" /></div>}
    />
  );
};
