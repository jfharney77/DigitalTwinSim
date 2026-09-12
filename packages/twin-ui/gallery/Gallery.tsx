import { useState } from "react";
import { ControlPanel } from "../src/components/ControlPanel";
import { MetricReadout } from "../src/components/MetricReadout";
import { Timeline, type TimelineStep } from "../src/components/Timeline";
import { TwinLayout } from "../src/components/TwinLayout";

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
      </div>
    </TwinLayout>
  );
}
