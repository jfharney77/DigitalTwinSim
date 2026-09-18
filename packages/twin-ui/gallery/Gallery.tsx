import { useState } from "react";
import { ControlPanel } from "../src/components/ControlPanel";
import { MetricReadout } from "../src/components/MetricReadout";
import { Timeline, type TimelineStep } from "../src/components/Timeline";
import { TwinLayout } from "../src/components/TwinLayout";
import { TourPlayer, type Tour, type TourRegion } from "../src/components/tour";

const TABS = [
  { id: "shell", label: "Shell" },
  { id: "anatomy", label: "Inside the machine" },
  { id: "usecases", label: "Use cases" },
] as const;

// A trace shaped like the ones the twins actually serve: a long stage in the
// middle, because every twin has one and its tests say so.
const TRACE: TimelineStep[] = [
  { phase: "off", label: "AC present, nothing drawing" },
  { phase: "power", label: "Power supplies energize", cycleCost: 2 },
  { phase: "power", label: "Standby rails up" },
  { phase: "boot", label: "Firmware boot", cycleCost: 6 },
  { phase: "boot", label: "Services start", cycleCost: 2 },
  { phase: "online", label: "Serving I/O" },
];

const TOKENS = [
  ["--dell-blue", "#0672cb"],
  ["--dell-blue-hover", "#0059a8"],
  ["--dell-tint", "#ebf5fc"],
  ["--dell-text", "#161616"],
  ["--dell-muted", "#636363"],
  ["--dell-border", "#d2d2d2"],
  ["--dell-page", "#f5f6f7"],
  ["--dell-error", "#ce1126"],
];

// A three-beat tour over a toy map, so the player can be checked with no twin
// behind it. Real tours come from GET /api/tour (twinkit.tour on the backend).
const TOUR_MAP = { width: 100, height: 50 };
const TOUR_REGIONS: (TourRegion & { label: string })[] = [
  { id: "node-a", label: "Node A", x: 6, y: 8, w: 36, h: 34 },
  { id: "link", label: "Interconnect", x: 44, y: 20, w: 12, h: 10 },
  { id: "node-b", label: "Node B", x: 58, y: 8, w: 36, h: 34 },
];
const TOUR_LAYERS = { "node-a": 1, link: 2, "node-b": 1 };
const TOUR: Tour = {
  id: "gallery",
  title: "A toy tour",
  intro: "Three beats over a stand-in map. Click a block to take over; Resume picks up where you left.",
  steps: [
    {
      id: "whole",
      title: "The whole machine",
      script: "Two identical nodes and the link between them. The camera starts on the whole map.",
      camera: { x: 0, y: 0, w: 100, h: 50 },
      regionIds: ["node-a", "node-b"],
      layerReveal: 0,
      traceCursor: 0,
      durationMs: 5000,
      photoId: null,
      audioUrl: null,
    },
    {
      id: "one-node",
      title: "One node, close up",
      script: "A close-up frames node A alone; node B mirrors it.",
      camera: { x: 2, y: 4, w: 44, h: 42 },
      regionIds: ["node-a"],
      layerReveal: 0,
      traceCursor: 2,
      durationMs: 5000,
      photoId: null,
      audioUrl: null,
    },
    {
      id: "the-link",
      title: "The link",
      script: "Peeling the outer layer leaves the interconnect lit on its own.",
      camera: { x: 30, y: 10, w: 40, h: 30 },
      regionIds: ["link"],
      layerReveal: 1,
      traceCursor: 5,
      durationMs: 5000,
      photoId: null,
      audioUrl: null,
    },
  ],
  photos: [],
  sources: [],
};

export function Gallery() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("shell");
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [cursor, setCursor] = useState(3);
  const state = TRACE[cursor];

  return (
    <TwinLayout
      title="twin-ui"
      subtitle="the shared shell, rendered with no twin behind it"
      tabs={TABS}
      active={tab}
      onTab={setTab}
      aside={<span className="levelctl-name">reference</span>}
    >
      <div className="gal">
        <h2>Tokens</h2>
        <div className="gal-swatches">
          {TOKENS.map(([name, value]) => (
            <div key={name} className="gal-swatch">
              <span className="gal-chip" style={{ background: `var(${name})` }} />
              {name}
              <br />
              {value}
            </div>
          ))}
        </div>

        <h2>Timeline</h2>
        <div className="gal-wide">
          <Timeline steps={TRACE} cursor={cursor} onCursor={setCursor} />
        </div>

        <h2>ControlPanel and MetricReadout</h2>
        <div className="gal-row">
          <ControlPanel
            running={running}
            done={cursor === TRACE.length - 1}
            speed={speed}
            status={state.label}
            onRun={() => setRunning(true)}
            onPause={() => setRunning(false)}
            onStep={() => setCursor((c) => Math.min(c + 1, TRACE.length - 1))}
            onReset={() => setCursor(0)}
            onSpeed={setSpeed}
            note="The sequence is a fixed trace computed by the backend; Run only plays it back."
          />
          <MetricReadout
            metrics={[
              { label: "phase", value: state.phase },
              { label: "step", value: `${cursor + 1} / ${TRACE.length}` },
              { label: "power draw", value: "1,840 W" },
              { label: "downtime", value: "0 s", hero: true },
            ]}
            note="Hero rows carry the number the twin exists to show."
          />
        </div>

        <h2>TourPlayer</h2>
        <div className="gal-wide">
          <TourPlayer
            tour={TOUR}
            layers={TOUR_LAYERS}
            bounds={TOUR_MAP}
            regions={TOUR_REGIONS}
            onTraceCursor={setCursor}
            renderStage={(stage) => (
              <svg
                viewBox={`${stage.viewBox.x} ${stage.viewBox.y} ${stage.viewBox.w} ${stage.viewBox.h}`}
                role="img"
                aria-label="Toy map"
              >
                {TOUR_REGIONS.map((r) => {
                  const look = stage.regionLook(r.id);
                  const on = stage.lit.has(r.id);
                  return (
                    <g
                      key={r.id}
                      transform={`translate(${look.dx} ${look.dy})`}
                      opacity={look.opacity}
                      onClick={() => stage.onRegionClick(r.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <rect
                        x={r.x}
                        y={r.y}
                        width={r.w}
                        height={r.h}
                        rx={1}
                        fill={on ? "var(--sm-edge)" : "var(--sm-idle)"}
                        stroke={on ? "var(--accent)" : "var(--line)"}
                        strokeWidth={0.5}
                      />
                      <text
                        x={r.x + r.w / 2}
                        y={r.y + r.h / 2}
                        fill="var(--txt)"
                        fontSize={3}
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        {r.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          />
        </div>
      </div>
    </TwinLayout>
  );
}
