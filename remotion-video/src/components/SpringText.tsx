import { spring, useCurrentFrame, useVideoConfig } from "remotion";

interface SpringTextProps {
  text: string;
  delayFrames?: number;
  fromY?: number;
  style?: React.CSSProperties;
}

/**
 * 弹性入场文字组件。
 * 文字从下方弹入，使用 spring 动画。
 */
export const SpringText: React.FC<SpringTextProps> = ({
  text,
  delayFrames = 0,
  fromY = 40,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const springProgress = spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 12, stiffness: 200 },
  });

  const translateY = interpolateProgress(springProgress, fromY);
  const opacity = springProgress;

  return (
    <span
      style={{
        display: "inline-block",
        opacity,
        transform: `translateY(${translateY}px)`,
        ...style,
      }}
    >
      {text}
    </span>
  );
};

function interpolateProgress(progress: number, fromY: number): number {
  return (1 - progress) * fromY;
}
