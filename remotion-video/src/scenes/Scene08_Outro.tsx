import { spring, useCurrentFrame, useVideoConfig, AbsoluteFill } from "remotion";

const C = {
  bgTop: "#F2FCE9",
  bgBottom: "#FFFFFF",
  green: "#58CC02",
  greenDark: "#46A302",
  greenLight: "#E5F8D1",
  text: "#4B4B4B",
  title: "#2B2B2B",
  muted: "#AFAFAF",
};

/**
 * 结尾 Outro — Duolingo 风格亮色调。
 *
 * 纯几何装饰（光环 + 菱形 + 金线），无 SVG 插图。
 * 与开场在视觉上呼应但更克制、更几何。
 */
export const Scene08Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 时序
  const bgGlow = spring({ frame: frame - 0, fps, config: { damping: 25, stiffness: 80 } });
  const ring1 = spring({ frame: frame - 8, fps, config: { damping: 15, stiffness: 120 } });
  const ring2 = spring({ frame: frame - 16, fps, config: { damping: 15, stiffness: 120 } });
  const lineDraw = spring({ frame: frame - 20, fps, config: { damping: 20, stiffness: 100 } });
  const logoS = spring({ frame: frame - 28, fps, config: { damping: 12, stiffness: 180 } });
  const badgelS = spring({ frame: frame - 50, fps, config: { damping: 14, stiffness: 150 } });
  const textS = spring({ frame: frame - 60, fps, config: { damping: 14, stiffness: 150 } });
  const footerS = spring({ frame: frame - 90, fps, config: { damping: 20, stiffness: 100 } });

  // 浮动菱形
  const diamonds = [
    { x: "12%", y: "18%", s: 7, d: 0 },
    { x: "85%", y: "14%", s: 5, d: 1.3 },
    { x: "6%", y: "75%", s: 6, d: 2.7 },
    { x: "92%", y: "68%", s: 4, d: 1.9 },
    { x: "45%", y: "88%", s: 5, d: 3.2 },
    { x: "76%", y: "82%", s: 4, d: 0.5 },
  ];

  // 光环参数
  const r1 = 180 + ring1 * 90;
  const r2 = 260 + ring2 * 60;

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${C.bgTop} 0%, ${C.bgBottom} 40%, ${C.bgBottom} 70%, ${C.bgTop} 100%)`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      overflow: "hidden",
    }}>
      {/* 背景光晕 */}
      <div style={{
        position: "absolute", width: 800, height: 800, borderRadius: "50%",
        background: `radial-gradient(circle, rgba(88,204,2,${0.10 * bgGlow}) 0%, rgba(88,204,2,${0.03 * bgGlow}) 30%, transparent 65%)`,
        top: "50%", left: "50%", transform: "translate(-50%, -50%)",
        pointerEvents: "none",
      }} />

      {/* 外光环 */}
      <div style={{
        position: "absolute", width: r2 * 2, height: r2 * 2, borderRadius: "50%",
        border: `1.2px solid rgba(88,204,2,${0.06 + ring2 * 0.12})`,
        top: "50%", left: "50%",
        transform: `translate(-50%, -50%) scale(${0.5 + ring2 * 0.5})`,
        pointerEvents: "none",
      }} />

      {/* 内光环 */}
      <div style={{
        position: "absolute", width: r1 * 2, height: r1 * 2, borderRadius: "50%",
        border: `1.5px solid rgba(88,204,2,${0.08 + ring1 * 0.16})`,
        top: "50%", left: "50%",
        transform: `translate(-50%, -50%) scale(${0.6 + ring1 * 0.4})`,
        pointerEvents: "none",
      }} />

      {/* 内虚线环 */}
      <div style={{
        position: "absolute", width: 300, height: 300, borderRadius: "50%",
        border: `1px dashed rgba(88,204,2,${0.06 + ring2 * 0.10})`,
        top: "50%", left: "50%",
        transform: `translate(-50%, -50%) rotate(${frame * 0.2}deg)`,
        pointerEvents: "none",
      }} />

      {/* 横向线 — 从中心向两边生长 */}
      <div style={{
        position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
        width: `${Math.min(360 * lineDraw, 360)}px`, height: 1,
        background: `linear-gradient(to right, transparent, ${C.greenLight} 25%, ${C.green} 50%, ${C.greenLight} 75%, transparent)`,
        pointerEvents: "none",
      }} />

      {/* 浮动菱形 */}
      {diamonds.map((d, i) => {
        const floatY = Math.sin(frame * 0.04 + d.d) * 8;
        const pulse = 0.3 + 0.3 * Math.sin(frame * 0.05 + d.d);
        return (
          <div key={i} style={{
            position: "absolute", left: d.x, top: d.y,
            width: d.s, height: d.s,
            background: C.green,
            opacity: 0.18 * bgGlow * (1 + pulse),
            transform: `rotate(45deg) translateY(${floatY}px)`,
            pointerEvents: "none",
          }} />
        );
      })}

      {/* 徽章 */}
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 8,
        padding: "5px 18px", background: C.greenLight, color: C.greenDark,
        borderRadius: 100, fontSize: 14, fontWeight: 700,
        fontFamily: "'Plus Jakarta Sans', 'PingFang SC', sans-serif",
        opacity: badgelS, transform: `translateY(${(1-badgelS)*10}px)`,
        marginBottom: 20, zIndex: 1,
      }}>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.green, animation: `pulse 2s infinite` }} />
        武汉理工大学 &middot; 华工杯 AI 创新大赛
      </div>

      {/* Logo */}
      <h1 style={{
        fontSize: 64, fontWeight: 800,
        fontFamily: "'Plus Jakarta Sans', 'PingFang SC', sans-serif",
        color: C.title,
        opacity: logoS, transform: `translateY(${(1-logoS)*30}px)`,
        margin: 0, zIndex: 1, letterSpacing: "-0.02em",
      }}>
        RealEnglish
      </h1>

      {/* CTA */}
      <p style={{
        fontSize: 26, fontWeight: 600,
        fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
        color: C.muted,
        opacity: textS, transform: `translateY(${(1-textS)*16}px)`,
        marginTop: 18, marginBottom: 0, zIndex: 1,
      }}>
        开始你的英语学习之旅
      </p>

      {/* 底部 */}
      <div style={{
        position: "absolute", bottom: 60, textAlign: "center",
        opacity: footerS, zIndex: 1,
      }}>
        <p style={{ fontSize: 14, color: C.muted, fontFamily: "'PingFang SC', sans-serif", margin: 0 }}>
          RealEnglish &middot; 真语英语
        </p>
      </div>
    </AbsoluteFill>
  );
};
