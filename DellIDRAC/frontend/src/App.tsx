import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchBringUp } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { BlockView } from "./components/BlockView";
import { BringUpControls } from "./components/BringUpControls";
import { BringUpCounters } from "./components/BringUpCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type { BringUpState, RegionKind, SubsystemMap } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "bringup" | "anatomy" | "components" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  return "bringup";
}

const PAGE_HASH: Record<Page, string> = {
  bringup: "",
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

// Keep in sync with KIND_STYLE in BlockView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  soc: "#2b2412",
  memory: "#241f33",
  network: "#12233a",
  sideband: "#122b2b",
  io: "#16281a",
  power: "#2b1a1a",
  security: "#12282e",
  sensor: "#1a2433",
};

const KIND_LABEL: Record<RegionKind, string> = {
  soc: "service processor (SoC)",
  memory: "working memory & flash",
  network: "management NIC",
  sideband: "host management buses",
  io: "remote presence (console, media)",
  power: "standby power",
  security: "root of trust & security",
  sensor: "monitoring & thermal engine",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<blockId>).
    if (!window.location.hash.startsWith(`#${PAGE_HASH[page]}`)) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<SubsystemMap | null>(null);
  const [trace, setTrace] = useState<BringUpState[]>([]);
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
    Promise.all([fetchAnatomy(), fetchBringUp()])
      .then(([an, bu]) => {
        setAnatomy(an);
        setTrace(bu.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(bu.trace);
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
      // Linger on the long stage (Lifecycle Controller init) so its
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
        <h1>iDRAC9</h1>
        <nav className="nav">
          <button
            className={page === "bringup" ? "active" : ""}
            onClick={() => setPage("bringup")}
          >
            Bring-up
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the controller
          </button>
          <button
            className={page === "components" ? "active" : ""}
            onClick={() => setPage("components")}
          >
            Capabilities &amp; options
          </button>
          <button
            className={page === "usecases" ? "active" : ""}
            onClick={() => setPage("usecases")}
          >
            Use cases
          </button>
        </nav>
        {page === "bringup" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedSeconds}s` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "bringup" && (
        <>
          <div className="an-hero">
            <h2>What wakes up before the server does</h2>
            <p>
              Plug in a PowerEdge and, seconds before the host can do anything,
              a small always-on computer boots inside it: iDRAC, the management
              controller. Standby power wakes its SoC, a Root of Trust verifies
              its firmware, embedded Linux comes up, and the management
              services — web console, Redfish, Lifecycle Controller, sensor
              monitoring — come online. Only then is the server reachable to be
              powered on. Play the trace and watch each stage light up the
              block it runs in.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <BlockView
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
                Highlighted blocks are the parts doing work at this step. Click
                a block to pin what it is; the full tour lives under Inside the
                controller.
              </div>
            </div>
          </div>

          <aside className="controls">
            <BringUpControls
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
            <BringUpCounters
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
