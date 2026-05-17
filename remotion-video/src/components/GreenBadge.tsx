interface GreenBadgeProps {
  text: string;
  color?: string;
  bgColor?: string;
  style?: React.CSSProperties;
}

/**
 * 绿色标签/徽章组件，Duolingo 风格圆角药丸形。
 */
export const GreenBadge: React.FC<GreenBadgeProps> = ({
  text,
  color = "#46A302",
  bgColor = "#E5F8D1",
  style,
}) => {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 16px",
        background: bgColor,
        color,
        borderRadius: 100,
        fontSize: 14,
        fontWeight: 700,
        fontFamily: "'Plus Jakarta Sans', 'PingFang SC', sans-serif",
        ...style,
      }}
    >
      {text}
    </span>
  );
};
