import { spring, useCurrentFrame, useVideoConfig, AbsoluteFill, Img, staticFile } from "remotion";

const C = {
  green: "#58CC02",
  darkGreen: "#46A302",
  lightGreen: "#E5F8D1",
  text: "#4B4B4B",
  title: "#2B2B2B",
  muted: "#AFAFAF",
};

/**
 * 场景 0 — 开场（0–8s / 0–240 帧）
 *
 * 布局仿落地页 Hero：左右各一个 SVG 浮动，中间标题叠层。
 * 左 typing.svg（较小，动画延迟），右 learning.svg（较大），叠加柔和光晕。
 */
export const Scene00Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 背景光晕渐现
  const bgGlow = spring({ frame: frame - 0, fps, config: { damping: 20, stiffness: 80 } });

  // 左侧 SVG：延迟 10 帧入场
  const leftSpring = spring({ frame: frame - 10, fps, config: { damping: 14, stiffness: 160 } });
  const leftFloat = Math.sin(frame * 0.055) * 12;

  // 右侧 SVG：延迟 5 帧入场
  const rightSpring = spring({ frame: frame - 5, fps, config: { damping: 14, stiffness: 160 } });
  const rightFloat = Math.sin(frame * 0.06 + 1) * 16;

  // Logo 标题：延迟 30 帧
  const logoS = spring({ frame: frame - 30, fps, config: { damping: 12, stiffness: 200 } });

  // 副标题：延迟 54 帧
  const subS = spring({ frame: frame - 54, fps, config: { damping: 18, stiffness: 140 } });

  // 底部小字：延迟 75 帧
  const footerS = spring({ frame: frame - 75, fps, config: { damping: 20, stiffness: 120 } });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #F2FCE9 0%, #FFFFFF 60%, #F5FDF0 100%)",
        overflow: "hidden",
      }}
    >
      {/* ── 背景光晕 ── */}
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse 600px 500px at 15% 80%, rgba(88,204,2,${0.12 * bgGlow}) 0%, transparent 70%),
                     radial-gradient(ellipse 500px 450px at 80% 75%, rgba(28,176,246,${0.08 * bgGlow}) 0%, transparent 70%),
                     radial-gradient(ellipse 350px 350px at 50% 20%, rgba(206,130,255,${0.06 * bgGlow}) 0%, transparent 70%)`,
      }} />

      {/* ── 左侧 SVG：typing.svg ── */}
      <div style={{
        position: "absolute", left: "4%", bottom: "8%",
        opacity: leftSpring,
        transform: `translateY(${leftFloat + (1 - leftSpring) * (-30)}px)`,
      }}>
        <Img src={staticFile("/svgs/typing.svg")}
          style={{ width: "min(420px, 32vw)", height: "auto" }} />
      </div>

      {/* ── 右侧 SVG：learning.svg ── */}
      <div style={{
        position: "absolute", right: "6%", bottom: "6%",
        opacity: rightSpring,
        transform: `translateY(${rightFloat + (1 - rightSpring) * (-20)}px)`,
      }}>
        <Img src={staticFile("/svgs/learning.svg")}
          style={{ width: "min(540px, 40vw)", height: "auto" }} />
      </div>

      {/* ── 中央文字 ── */}
      <div style={{
        position: "absolute", inset: 0, display: "flex",
        flexDirection: "column", alignItems: "center", justifyContent: "center",
        zIndex: 1, pointerEvents: "none",
      }}>
        {/* 徽章 */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          padding: "5px 18px", background: C.lightGreen, color: C.darkGreen,
          borderRadius: 100, fontSize: 14, fontWeight: 700,
          fontFamily: "'Plus Jakarta Sans', 'PingFang SC', sans-serif",
          opacity: logoS, transform: `translateY(${(1 - logoS) * 16}px)`,
          marginBottom: 24,
        }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.green }} />
          武汉理工大学 · 华工杯 AI 创新大赛
        </div>

        {/* 主标题 */}
        <h1 style={{
          fontSize: "clamp(56px, 6vw, 80px)", fontWeight: 800,
          fontFamily: "'Plus Jakarta Sans', 'PingFang SC', sans-serif",
          color: C.title, margin: 0, lineHeight: 1.1,
          opacity: logoS,
          transform: `translateY(${(1 - logoS) * 40}px)`,
        }}>
          用<span style={{ color: C.green, position: "relative" }}>
            真实影视
            <span style={{
              position: "absolute", bottom: 2, left: 0, right: 0,
              height: 8, background: C.lightGreen, borderRadius: 4,
              zIndex: -1, opacity: 0.6,
            }} />
          </span>学地道英语
        </h1>

        {/* 副标题 */}
        <p style={{
          fontSize: 18, color: C.muted, marginTop: 16, marginBottom: 0,
          fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
          maxWidth: 460, textAlign: "center", lineHeight: 1.7,
          opacity: subS,
          transform: `translateY(${(1 - subS) * 12}px)`,
        }}>
          AI 驱动的英语视听说学习平台 &mdash; 看 → 听 → 说 → 评，四步闭环提升英语能力
        </p>

        {/* 底部信息 */}
        <p style={{
          position: "absolute", bottom: 48, fontSize: 14, color: C.muted,
          fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
          opacity: footerS,
        }}>
          RealEnglish · 真语英语
        </p>
      </div>
    </AbsoluteFill>
  );
};
