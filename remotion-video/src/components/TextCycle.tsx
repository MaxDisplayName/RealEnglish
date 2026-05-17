import type { ReactNode } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig, Img, staticFile } from "remotion";
import { GreenBadge } from "./GreenBadge";

export interface TextCycleItem {
  startFrame: number;
  title: string;
  subtitle?: string;
  tags?: string[];
  tagColor?: string;
  tagBgColor?: string;
  features?: { icon: string; label: string }[];
  /** 该阶段专属 SVG 路径（public/svgs/ 下） */
  svgSrc?: string;
  /** SVG 宽度，默认 200 */
  svgWidth?: number;
}

interface TextCycleProps {
  items: TextCycleItem[];
  transitionFrames?: number;
  accentColor?: string;
  footer?: ReactNode;
  style?: React.CSSProperties;
}

/**
 * 多阶段文字轮换组件 — 富文本版。
 * 每阶段：标签行 → 标题（绿色左边框+生长动画）→ 描述 → 功能列表（stagger 交错入场）→ SVG。
 */
export const TextCycle: React.FC<TextCycleProps> = ({
  items,
  transitionFrames = 12,
  accentColor = "#58CC02",
  footer,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28, ...style }}>
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        const enterEnd = item.startFrame + transitionFrames;

        const enter = interpolate(frame, [item.startFrame, enterEnd], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });

        let exit = 1;
        if (!isLast) {
          const nextStart = items[i + 1].startFrame;
          const exitStart = nextStart - transitionFrames;
          exit = interpolate(frame, [exitStart, nextStart], [1, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });
        }

        const opacity = enter * exit;
        const yOff = (1 - enter) * 14;
        if (opacity <= 0) return null;

        // 强调线生长动画（spring，~300ms）
        const barSpring = spring({
          frame: frame - item.startFrame,
          fps,
          config: { damping: 15, stiffness: 180 },
        });

        // 标签和功能点延迟入场
        const detailEnter = interpolate(
          frame, [item.startFrame + 5, enterEnd + 5], [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <div
            key={i}
            style={{
              position: "absolute", inset: 0,
              display: "flex", flexDirection: "column", justifyContent: "center",
              opacity, transform: `translateY(${yOff}px)`,
              pointerEvents: opacity < 0.05 ? "none" : "auto",
            }}
          >
            {/* 标签 */}
            {item.tags && item.tags.length > 0 && (
              <div style={{ opacity: detailEnter, marginBottom: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
                {item.tags.map((tag, j) => (
                  <GreenBadge key={j} text={tag} color={item.tagColor} bgColor={item.tagBgColor} />
                ))}
              </div>
            )}

            {/* 标题 + 绿色左边框（生长动画） */}
            <div style={{ display: "flex", alignItems: "stretch", gap: 0 }}>
              <div
                style={{
                  width: 5, borderRadius: "2.5px",
                  background: accentColor,
                  transform: `scaleY(${barSpring})`,
                  transformOrigin: "top",
                  flexShrink: 0,
                  marginRight: 20,
                }}
              />
              <div>
                <h2 style={{
                  fontSize: 48, fontWeight: 800, color: "#2B2B2B", margin: 0,
                  fontFamily: "'Plus Jakarta Sans', 'PingFang SC', sans-serif",
                  lineHeight: 1.2, whiteSpace: "pre-line",
                }}>
                  {item.title}
                </h2>

                {item.subtitle && (
                  <p style={{
                    fontSize: 19, color: "#AFAFAF", margin: "10px 0 0",
                    fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
                    lineHeight: 1.6,
                  }}>
                    {item.subtitle}
                  </p>
                )}
              </div>
            </div>

            {/* 功能点列表 — stagger 交错入场 */}
            {item.features && item.features.length > 0 && (
              <div style={{
                opacity: detailEnter,
                display: "flex", flexDirection: "column", gap: 12,
                marginTop: 22,
              }}>
                {item.features.map((f, k) => {
                  // 每条延迟 4 帧
                  const lineEnter = interpolate(
                    frame, [item.startFrame + 5 + k * 4, enterEnd + 5 + k * 4], [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  return (
                    <div key={k} style={{
                      display: "flex", alignItems: "center", gap: 14,
                      fontSize: 17, color: "#4B4B4B",
                      fontFamily: "'PingFang SC', sans-serif",
                      opacity: lineEnter,
                      transform: `translateX(${(1-lineEnter)*12}px)`,
                    }}>
                      <span style={{ fontSize: 20, opacity: 0.8, flexShrink: 0, width: 26, textAlign: "center" }}>{f.icon}</span>
                      <span>{f.label}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 每阶段专属 SVG */}
            {item.svgSrc && (
              <div style={{ opacity: detailEnter, marginTop: 16 }}>
                <Img src={staticFile(item.svgSrc)} style={{ width: item.svgWidth || 200, opacity: 1 }} />
              </div>
            )}

            {/* 兜底 footer SVG（如果 item 没指定 svgSrc） */}
            {!item.svgSrc && footer && (
              <div style={{ opacity: detailEnter, marginTop: 18 }}>
                {footer}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
