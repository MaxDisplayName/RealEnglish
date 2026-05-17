import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * 8 场景的帧边界（累计帧）。
 * 0: 0-240, 1: 240-480, 2: 480-900, 3: 900-1500,
 * 4: 1500-2100, 5: 2100-3090, 6: 3090-3780, 7: 3780-5400
 */
const SCENE_BOUNDARIES = [0, 240, 480, 900, 1500, 2100, 3090, 3780, 5160, 5400];

interface ProgressDotsProps {
  totalScenes?: number;
}

/**
 * 底部进度指示器 — 8 个圆点。
 *
 * - 当前场景：亮绿色 #58CC02，弹性放大
 * - 已播场景：浅绿 #C6F09B
 * - 未播场景：灰色 #E5E5E5
 */
export const ProgressDots: React.FC<ProgressDotsProps> = ({
  totalScenes = 9,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 找到当前场景索引
  let currentScene = 0;
  for (let i = 0; i < totalScenes; i++) {
    if (frame >= SCENE_BOUNDARIES[i] && frame < SCENE_BOUNDARIES[i + 1]) {
      currentScene = i;
      break;
    }
  }

  return (
    <div
      style={{
        position: "absolute",
        bottom: 28,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        gap: 10,
        zIndex: 1000,
      }}
    >
      {Array.from({ length: totalScenes }).map((_, i) => {
        const isCurrent = i === currentScene;
        const isPast = i < currentScene;

        // 当前点弹性动画
        const dotSpring = spring({
          frame: frame - (SCENE_BOUNDARIES[i] + 10),
          fps,
          config: { damping: 10, stiffness: 200 },
        });

        const scale = isCurrent ? 1 + dotSpring * 0.4 : 1;
        const bg = isCurrent
          ? "#58CC02"
          : isPast
            ? "#C6F09B"
            : "#E5E5E5";

        return (
          <span
            key={i}
            style={{
              display: "block",
              width: isCurrent ? 20 : 10,
              height: 10,
              borderRadius: 5,
              background: bg,
              transform: `scale(${scale})`,
              transition: "background 0.3s ease",
            }}
          />
        );
      })}
    </div>
  );
};
