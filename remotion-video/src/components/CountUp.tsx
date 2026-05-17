import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface CountUpProps {
  from: number;
  to: number;
  startFrame: number;
  durationFrames: number;
  style?: React.CSSProperties;
}

/**
 * 数字滚动动画组件。
 * 在给定的帧范围内，数字从 from 计数到 to。
 */
export const CountUp: React.FC<CountUpProps> = ({
  from,
  to,
  startFrame,
  durationFrames,
  style,
}) => {
  const frame = useCurrentFrame();
  const value = interpolate(
    frame - startFrame,
    [0, durationFrames],
    [from, to],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );

  return (
    <span style={{ fontVariantNumeric: "tabular-nums", ...style }}>
      {Math.round(value).toLocaleString()}
    </span>
  );
};
