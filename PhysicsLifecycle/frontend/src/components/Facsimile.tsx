// Stylized product facsimiles (V1/V9, physics_specs/VISUAL_IMPROVEMENTS.md).
// Drawn inline so no asset files are needed for products with no
// ship-safe photo. Always presented with the "illustration" label —
// these are recognizable silhouettes, not Dell product photos.

export type FacsimileShape =
  | "laptop" | "tower" | "server" | "rack" | "storage" | "switch"
  | "console";

const INK = "#0d1420";
const EDGE = "#2a3a52";
const LED = "#2596be";
const LED2 = "#7fbf5a";

function Slots({ x, y, w, n, sh }: { x: number; y: number; w: number; n: number; sh: number }) {
  return (
    <g>
      {Array.from({ length: n }, (_, i) => (
        <rect
          key={i}
          x={x + (i * w) / n + 0.6}
          y={y}
          width={w / n - 1.2}
          height={sh}
          rx={0.5}
          fill={EDGE}
        />
      ))}
    </g>
  );
}

export function Facsimile({ shape, size = 100 }: { shape: FacsimileShape; size?: number }) {
  const h = size * 0.62;
  return (
    <svg
      viewBox="0 0 100 62"
      width={size}
      height={h}
      aria-label={`${shape} illustration`}
    >
      <rect x={0} y={0} width={100} height={62} rx={3} fill={INK} />
      {shape === "laptop" && (
        <g>
          <rect x={18} y={8} width={64} height={34} rx={2} fill={EDGE} />
          <rect x={21} y={11} width={58} height={28} rx={1} fill="#16233a" />
          <path d="M12 44 L88 44 L94 52 L6 52 Z" fill={EDGE} />
          <rect x={38} y={45.5} width={24} height={3.5} rx={1} fill="#16233a" />
        </g>
      )}
      {shape === "tower" && (
        <g>
          <rect x={32} y={4} width={36} height={54} rx={3} fill={EDGE} />
          <rect x={36} y={8} width={28} height={20} rx={1.5} fill="#16233a" />
          <circle cx={40} cy={52} r={1.6} fill={LED} />
          <Slots x={36} y={32} w={28} n={3} sh={12} />
        </g>
      )}
      {shape === "server" && (
        <g>
          <rect x={8} y={18} width={84} height={26} rx={2} fill={EDGE} />
          <Slots x={12} y={22} w={56} n={8} sh={18} />
          <rect x={72} y={22} width={16} height={18} rx={1} fill="#16233a" />
          <circle cx={76} cy={26} r={1.4} fill={LED2} />
          <circle cx={80} cy={26} r={1.4} fill={LED} />
        </g>
      )}
      {shape === "rack" && (
        <g>
          <rect x={28} y={2} width={44} height={58} rx={2} fill={EDGE} />
          {Array.from({ length: 9 }, (_, i) => (
            <rect
              key={i}
              x={31}
              y={4.5 + i * 6.1}
              width={38}
              height={4.6}
              rx={0.8}
              fill={i === 4 ? "#1d3a5f" : "#16233a"}
            />
          ))}
          {Array.from({ length: 9 }, (_, i) => (
            <circle key={i} cx={66} cy={6.8 + i * 6.1} r={0.9} fill={LED2} />
          ))}
        </g>
      )}
      {shape === "storage" && (
        <g>
          <rect x={8} y={14} width={84} height={34} rx={2} fill={EDGE} />
          <Slots x={12} y={18} w={76} n={12} sh={26} />
        </g>
      )}
      {shape === "switch" && (
        <g>
          <rect x={6} y={22} width={88} height={18} rx={2} fill={EDGE} />
          {Array.from({ length: 16 }, (_, i) => (
            <rect
              key={i}
              x={10 + i * 4.6}
              y={26}
              width={3.4}
              height={4.5}
              rx={0.5}
              fill="#16233a"
            />
          ))}
          {Array.from({ length: 16 }, (_, i) => (
            <circle
              key={i}
              cx={11.7 + i * 4.6}
              cy={35}
              r={0.8}
              fill={i % 3 ? LED2 : LED}
            />
          ))}
        </g>
      )}
      {shape === "console" && (
        <g>
          <rect x={14} y={6} width={72} height={44} rx={2} fill={EDGE} />
          <rect x={17} y={9} width={66} height={38} rx={1} fill="#16233a" />
          <rect x={20} y={12} width={28} height={10} rx={1} fill="#1d3a5f" />
          <rect x={52} y={12} width={28} height={10} rx={1} fill="#1d3a5f" />
          <polyline
            points="21,42 30,36 38,39 46,31 54,34 62,28 70,31 79,25"
            fill="none"
            stroke={LED}
            strokeWidth={1.4}
          />
        </g>
      )}
    </svg>
  );
}
