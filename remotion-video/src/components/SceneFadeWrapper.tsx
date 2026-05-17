import type { ReactNode } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface SceneFadeWrapperProps {
  children: ReactNode;
  /** 末尾 fade-to-white 的帧数（默认 20） */
  exitFrames?: number;
}

/**
 * 场景包裹器。
 *
 * - 场景开头 8 帧：白色 → 透明（入场消白）
 * - 场景末尾 exitFrames 帧：透明 → 白色（退场遮罩）
 *
 * 配合 TransitionSeries crossfade 使用，退场时内容先白屏，
 * 避免旧场景文字与新场景叠加。
 */
export const SceneFadeWrapper: React.FC<SceneFadeWrapperProps> = ({
  children,
  exitFrames = 20,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // 末尾 fade-to-white
  const exitOverlay = interpolate(
    frame,
    [durationInFrames - exitFrames, durationInFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // 开头白色消退（入场）
  const enterOverlay = interpolate(
    frame,
    [0, 8],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const overlay = Math.max(exitOverlay, enterOverlay);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {children}
      {overlay > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "#FFFFFF",
            opacity: overlay,
            pointerEvents: "none",
            zIndex: 999,
          }}
        />
      )}
    </div>
  );
};
