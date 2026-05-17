import { useCurrentFrame } from "remotion";

const W = 1920;
const H = 1080;
const S = 60;
const MARGIN = 600;

/**
 * SVG 45° 菱形科技网格 — 全局层。
 *
 * 覆盖全视频，双方向对角线交叉 + 边沿渐变消退 + 交点光点。
 */
export const TechGrid: React.FC = () => {
  const frame = useCurrentFrame();

  const d1 = (frame * 0.06) % (S * 2);
  const d2 = (frame * 0.10) % (S * 2);

  const cMin = -(H + MARGIN);
  const cMax = W + H + MARGIN;
  const nLines = Math.ceil((cMax - cMin) / S);

  const lines45 = Array.from({ length: nLines }, (_, i) => {
    const c = cMin + (i - 1) * S + d1;
    return { x1: c - H - MARGIN, y1: H + MARGIN, x2: c + MARGIN, y2: -MARGIN };
  });

  const linesMinus45 = Array.from({ length: nLines }, (_, i) => {
    const c = (i - 1) * S + cMin + S - d2;
    return { x1: -MARGIN, y1: c - MARGIN, x2: W + MARGIN, y2: W + c + MARGIN };
  });

  const dots: { x: number; y: number }[] = [];
  for (let i = 0; i < nLines; i++) {
    for (let j = 0; j < nLines; j++) {
      if ((i + j * 2) % 4 !== 0) continue;
      const c1 = cMin + (i - 1) * S + d1;
      const c2 = (j - 1) * S + cMin + S - d2;
      const x = (c1 - c2) / 2;
      const y = (c1 + c2) / 2;
      if (x > -20 && x < W + 20 && y > -20 && y < H + 20) dots.push({ x, y });
    }
  }

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 998,
        // 边缘渐变掩膜：四边淡出
        WebkitMaskImage: `
          linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%),
          linear-gradient(to bottom, transparent 0%, black 10%, black 90%, transparent 100%)
        `,
        maskImage: `
          linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%),
          linear-gradient(to bottom, transparent 0%, black 10%, black 90%, transparent 100%)
        `,
        maskComposite: "intersect",
        WebkitMaskComposite: "intersect",
      }}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%" }}
      >
        {/* 细线菱形网格 — 超低 opacity */}
        <g stroke="#58CC02" strokeWidth={0.6} opacity={0.07}>
          {lines45.map((l, i) => (
            <line key={`p${i}`} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
          {linesMinus45.map((l, i) => (
            <line key={`m${i}`} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
        </g>

        {/* 粗线 — 每 5 条 */}
        <g stroke="#58CC02" strokeWidth={1.5} opacity={0.08}>
          {lines45.filter((_, i) => i % 5 === 0).map((l, i) => (
            <line key={`P${i}`} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
          {linesMinus45.filter((_, i) => i % 5 === 0).map((l, i) => (
            <line key={`M${i}`} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
        </g>

        {/* 交点光点 — 每 4×4 取 1 */}
        <g fill="#58CC02">
          {dots.map((d, i) => (
            <circle key={`d${i}`} cx={d.x} cy={d.y} r={2.5} opacity={0.15} />
          ))}
        </g>

        {/* 底部 HUD 横线 */}
        <g stroke="#58CC02">
          <line x1={240} y1={940} x2={1680} y2={940} strokeWidth={0.5} opacity={0.10} />
          <line x1={360} y1={980} x2={1560} y2={980} strokeWidth={0.6} opacity={0.13} />
          <line x1={160} y1={1020} x2={1760} y2={1020} strokeWidth={0.3} opacity={0.07} />
        </g>
      </svg>
    </div>
  );
};
