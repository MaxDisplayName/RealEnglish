import type { ReactNode } from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

interface BrowserMockupProps {
  children: ReactNode;
  style?: React.CSSProperties;
}

/**
 * 浏览器窗口外框组件。
 * 顶部三色圆点，入场时 shadow 从 0 过渡。
 */
export const BrowserMockup: React.FC<BrowserMockupProps> = ({
  children,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 阴影入场动画
  const shadowSpring = spring({
    frame: frame - 5,
    fps,
    config: { damping: 18, stiffness: 120 },
  });
  const shadowAlpha = shadowSpring * 0.12;
  const shadowBlur = shadowSpring * 40;

  return (
    <div
      style={{
        borderRadius: 16,
        border: "2px solid #E5E5E5",
        overflow: "hidden",
        boxShadow: `0 8px ${shadowBlur}px rgba(0,0,0,${shadowAlpha})`,
        background: "#FFFFFF",
        ...style,
      }}
    >
      {/* 顶部栏 */}
      <div
        style={{
          height: 40,
          background: "#F7F7F7",
          display: "flex",
          alignItems: "center",
          paddingLeft: 16,
          gap: 8,
          borderBottom: "1px solid #E5E5E5",
        }}
      >
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#EF4444" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#F59E0B" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#58CC02" }} />
      </div>
      <div style={{ position: "relative" }}>{children}</div>
    </div>
  );
};
