import type { ReactNode } from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";



interface SceneLayoutProps {
  videoSide: "left" | "right";
  videoSlot: ReactNode;
  contentSlot: ReactNode;
  background?: string;
  glowColor?: string;
}

/**
 * 场景通用布局。左右分栏 + 底部进度点 + 背景光晕脉动。
 */
export const SceneLayout: React.FC<SceneLayoutProps> = ({
  videoSide,
  videoSlot,
  contentSlot,
  background = "linear-gradient(180deg, #FFFFFF 0%, #F2FCE9 100%)",
  glowColor = "rgba(88,204,2,0.07)",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entry = spring({ frame: frame - 0, fps, config: { damping: 20, stiffness: 100 } });

  // 光晕缓慢脉动（4s周期，scale 0.92~1.08）
  const glowPulse = 1 + Math.sin(frame * 0.025) * 0.08;

  const videoOrder = videoSide === "left" ? 0 : 1;
  const contentOrder = videoSide === "left" ? 1 : 0;

  return (
    <div
      style={{
        position: "absolute", inset: "0 0 100px 0",
        background,
        display: "flex", alignItems: "center", justifyContent: "center",
        gap: 56, padding: "0 64px",
        overflow: "hidden",
        opacity: entry,
      }}
    >
      {/* 背景光晕 — 脉动 */}
      <div
        style={{
          position: "absolute",
          width: 750, height: 750, borderRadius: "50%",
          background: `radial-gradient(circle, ${glowColor} 0%, transparent 70%)`,
          top: "30%",
          left: videoSide === "left" ? "70%" : "30%",
          transform: `translate(-50%, -50%) scale(${glowPulse})`,
          pointerEvents: "none",
        }}
      />

      {/* 视频区 */}
      <div style={{ flex: "0 0 auto", order: videoOrder, zIndex: 1, alignSelf: "center" }}>
        {videoSlot}
      </div>

      {/* 内容区 */}
      <div
        style={{
          flex: 1, order: contentOrder, zIndex: 1,
          display: "flex", flexDirection: "column", justifyContent: "center",
          minWidth: 0, maxWidth: 520,
        }}
      >
        {contentSlot}
      </div>
    </div>
  );
};
