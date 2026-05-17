import { OffthreadVideo, staticFile } from "remotion";
import { BrowserMockup } from "../components/BrowserMockup";
import { SceneLayout } from "../components/SceneLayout";
import { TextCycle } from "../components/TextCycle";

const items = [
  {
    startFrame: 0, svgSrc: "/svgs/undraw_sync_pe2t.svg", svgWidth: 200,
    title: "账号登录",
    subtitle: "学生 / 教师双角色，JWT 安全认证",
    tags: ["学习起点"],
    features: [
      { icon: "👤", label: "邮箱 + 密码注册登录" },
      { icon: "🎓", label: "学生 / 教师身份选择" },
      { icon: "🔑", label: "教师邀请码绑定班级" },
    ],
  },
  {
    startFrame: 90, svgSrc: "/svgs/fill-the-blank.svg", svgWidth: 200,
    title: "智能定级测试",
    subtitle: "10 道混合难度题目，每道关联真实影视片段",
    tags: ["定级测试"],
    features: [
      { icon: "📝", label: "10 题混合难度随机抽样（A3+B4+C3）" },
      { icon: "🎥", label: "每道题关联 B 站视频片段播放" },
      { icon: "✅", label: "即时反馈，自动评定等级" },
    ],
  },
  {
    startFrame: 300, svgSrc: "/svgs/undraw_presentation_4ik4.svg", svgWidth: 220,
    title: "A / B / C\n三级评定",
    subtitle: "A（高级 ≥75%）· B（中级 50-74%）· C（初级 <50%）",
    tags: ["A级 绿色", "B级 蓝色", "C级 紫色"],
    features: [
      { icon: "🟢", label: "A 级（高级）— 难度自适应拔高" },
      { icon: "🔵", label: "B 级（中级）— 巩固基础稳步提升" },
      { icon: "🟣", label: "C 级（初级）— 基础训练循序渐进" },
    ],
  },
];

export const Scene02Placement: React.FC = () => {
  return (
    <SceneLayout videoSide="right" glowColor="rgba(28,176,246,0.06)"
      videoSlot={
        <BrowserMockup style={{ width: 1120, height: 670 }}>
          <OffthreadVideo src={staticFile("/recordings/part2.mp4")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </BrowserMockup>
      }
      contentSlot={<div style={{ position: "relative", height: 440 }}><TextCycle items={items} /></div>}
    />
  );
};
