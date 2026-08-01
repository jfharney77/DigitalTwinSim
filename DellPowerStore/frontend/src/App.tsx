import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchPowerOn } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ChassisView } from "./components/ChassisView";
import { PowerOnControls } from "./components/PowerOnControls";
import { PowerOnCounters } from "./components/PowerOnCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type { ChassisAnatomy, PowerOnState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "poweron" | "anatomy" | "components" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  return "poweron";
}

const PAGE_HASH: Record<Page, string> = {
  poweron: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
};

// Deep-link into the trace: /#step=N or /#phase=<name>. Returns the starting
// cursor, or null when the hash matches neither pattern (or names an unknown
// phase) — in which case playback starts at 0 as before.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const h = window.location.hash;
  const step = h.match(/#step=(\d+)$/);
  if (step) return Math.min(Number(step[1]), states.length - 1);
  const phase = h.match(/#phase=([a-z0-9_-]+)$/i);
  if (phase) {
    const i = states.findIndex((s) => s.phase === phase[1]);
    return i >= 0 ? i : null;
  }
  return null;
}

// Keep in sync with KIND_STYLE in ChassisView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  storage: "#12233a",
  nvram: "#1c1f3f",
  cpu: "#2b2412",
  memory: "#241f33",
  io: "#16281a",
  power: "#2b1a1a",
  cooling: "#122b2b",
  battery: "#22290f",
  management: "#12282e",
  board: "#1a2433",
};

const KIND_LABEL: Record<RegionKind, string> = {
  storage: "NVMe drive bay",
  nvram: "NVRAM write cache",
  cpu: "node CPU",
  memory: "node DIMMs",
  io: "I/O modules & ports",
  power: "power supply",
  cooling: "fan pack",
  battery: "battery backup (vault)",
  management: "management/service ports",
  board: "node system board",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<regionId>).
    if (!window.location.hash.startsWith(`#${PAGE_HASH[page]}`)) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<ChassisAnatomy | null>(null);
  const [trace, setTrace] = useState<PowerOnState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply a #step=/#phase= deep link only on the first successful trace load,
  // so a reading-level refetch does not yank the cursor back.
  const hashApplied = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  }, []);

  // The trace is pure data from the backend engine; fetch it once and play
  // it back here — the clock lives in the frontend, never in the engine.
  useEffect(() => {
    Promise.all([fetchAnatomy(), fetchPowerOn()])
      .then(([an, po]) => {
        setAnatomy(an);
        setTrace(po.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(po.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  const state = trace[cursor] ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (node OS boot, pool assembly) so their
      // real-world cost is visible.
      if (dwell.current > 1) {
        dwell.current -= 1;
        return;
      }
      setCursor((c) => {
        const next = c + 1;
        if (next >= trace.length - 1) {
          stop();
          return trace.length - 1;
        }
        dwell.current = Math.min(trace[next]?.cycleCost ?? 1, MAX_DWELL);
        return next;
      });
    };
    const ms = Math.max(40, 600 / speedRef.current);
    timer.current = window.setInterval(tick, ms);
  }, [trace, stop]);

  const step = useCallback(() => {
    stop();
    setCursor((c) => Math.min(c + 1, trace.length - 1));
  }, [trace, stop]);

  const reset = useCallback(() => {
    stop();
    setCursor(0);
  }, [stop]);

  // Retune the interval live when speed changes mid-run.
  useEffect(() => {
    if (timer.current === null) return;
    stop();
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  const selectedRegion =
    anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <div className="app dell">
      <header>
        <h1>PowerStore</h1>
        <nav className="nav">
          <button
            className={page === "poweron" ? "active" : ""}
            onClick={() => setPage("poweron")}
          >
            Power-on
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the chassis
          </button>
          <button
            className={page === "components" ? "active" : ""}
            onClick={() => setPage("components")}
          >
            Components &amp; options
          </button>
          <button
            className={page === "usecases" ? "active" : ""}
            onClick={() => setPage("usecases")}
          >
            Use cases
          </button>
        </nav>
        {page === "poweron" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedSeconds}s` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "poweron" && (
        <>
          <div className="an-hero">
            <h2>What happens when you plug it in</h2>
            <p>
              A storage array has no power button — it starts booting the
              moment AC arrives. Two controller nodes come up side by side,
              check the battery that protects their write cache, discover the
              NVMe drives they both share, and form an active-active pair
              before a single volume goes online. Play the trace and watch
              each stage light up the hardware it runs on.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <ChassisView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  selected={regionId}
                  onSelect={setRegionId}
                />
              )}
              {state && (
                <div className="poweron-desc">
                  <strong>{state.label}.</strong> {state.description}
                </div>
              )}
              <div className="mini an-hint">
                Highlighted blocks are the parts doing work at this step.
                Click a block to pin what it is; the full tour lives under
                Inside the chassis.
              </div>
            </div>
          </div>

          <aside className="controls">
            <PowerOnControls
              speed={speed}
              running={running}
              done={done}
              phaseLabel={state?.label ?? "—"}
              onSpeed={setSpeed}
              onRun={run}
              onPause={stop}
              onStep={step}
              onReset={reset}
            />
            <PowerOnCounters
              state={state}
              stepIndex={cursor}
              stepCount={trace.length}
            />
            {selectedRegion && (
              <section className="an-panel">
                <h2>{selectedRegion.label}</h2>
                <p className="an-desc">{selectedRegion.description}</p>
              </section>
            )}
            {anatomy && (
              <section className="legend an-panel">
                <h2>Blocks</h2>
                {kinds.map((k) => (
                  <span key={k}>
                    <i
                      style={{
                        background: KIND_SWATCH[k],
                        border: "1px solid var(--sm-edge)",
                      }}
                    />
                    {KIND_LABEL[k]}
                  </span>
                ))}
              </section>
            )}
          </aside>
        </>
      )}
    </div>
  );
}
