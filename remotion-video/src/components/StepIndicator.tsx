import { interpolate, useCurrentFrame } from "remotion";

interface Step {
  label: string;
  active: boolean;
}

interface StepIndicatorProps {
  steps: Step[];
  startFrame: number;
  style?: React.CSSProperties;
}

/**
 * 步骤指示器组件。
 * 当前活跃步骤亮起绿色，其余灰色。
 */
export const StepIndicator: React.FC<StepIndicatorProps> = ({
  steps,
  startFrame,
  style,
}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        ...style,
      }}
    >
      {steps.map((step, i) => {
        const itemFrame = frame - startFrame - i * 30;
        const opacity = interpolate(itemFrame, [0, 15], [0, 1], {
          extrapolateRight: "clamp",
          extrapolateLeft: "clamp",
        });

        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              opacity,
            }}
          >
            <span
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                fontWeight: 800,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                background: step.active ? "#58CC02" : "#E5E5E5",
                color: step.active ? "#FFFFFF" : "#AFAFAF",
                transition: "all 0.3s ease",
              }}
            >
              {i + 1}
            </span>
            <span
              style={{
                fontSize: 15,
                fontWeight: 600,
                fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
                color: step.active ? "#2B2B2B" : "#AFAFAF",
              }}
            >
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
