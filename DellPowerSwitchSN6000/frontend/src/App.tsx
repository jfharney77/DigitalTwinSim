import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchFabric } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { FabricView } from "./components/FabricView";
import { FabricControls } from "./components/FabricControls";
import { FabricCounters } from "./components/FabricCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type { FabricAnatomy, FabricState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "fabric" | "anatomy" | "components" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  return "fabric";
}

const PAGE_HASH: Record<Page, string> = {
  fabric: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
};

// #step=N / #phase=<name> deep-links start playback at a chosen step; both
// fall through pageFromHash() and land on the default page.
function initialStepFromHash(states: { phase: string }[]): number | null {
  const h = window.location.hash;
  const step = h.match(/^#step=(\d+)$/);
  if (step) return Math.min(Number(step[1]), states.length - 1);
  const phase = h.match(/^#phase=([a-z0-9_-]+)$/i);
  if (phase) {
    const i = states.findIndex((s) => s.phase === phase[1]);
    return i >= 0 ? i : null;
  }
  return null;
}

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    if (!window.location.hash.startsWith(`#${PAGE_HASH[page]}`)) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<FabricAnatomy | null>(null);
  const [trace, setTrace] = useState<FabricState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply the #step=/#phase= deep-link only on the first load — a
  // reading-level refetch must not yank the cursor back.
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
    Promise.all([fetchAnatomy(), fetchFabric()])
      .then(([an, fb]) => {
        setAnatomy(an);
        setTrace(fb.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const s = initialStepFromHash(fb.trace);
          if (s !== null) setCursor(s);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  const state = trace[cursor] ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (link training) so their real-world cost is
      // visible.
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
        <h1>PowerSwitch SN6000</h1>
        <nav className="nav">
          <button
            className={page === "fabric" ? "active" : ""}
            onClick={() => setPage("fabric")}
          >
            Fabric in motion
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the fabric
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
        {page === "fabric" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedSeconds}s` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "fabric" && (
        <>
          <div className="an-hero">
            <h2>What an AI fabric refuses to do</h2>
            <p>
              Ordinary Ethernet drops packets when a buffer fills — the
              sender notices, backs off, retransmits, and the network keeps
              working. That bargain is catastrophic for distributed
              training, where every GPU must finish the same all-reduce
              before any of them can start the next step, so one
              retransmission stalls the entire fleet. This fabric is built
              never to drop: it signals congestion early, pauses
              selectively, and spreads flows across the alternate paths
              leaf/spine holds in reserve. Play the trace and watch the
              dropped-packet counter stay at zero while the busiest link
              hits 98%.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <FabricView
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
                Watch the congestion step and then the reroute: the busiest
                link falls from 98% to 71% while total throughput <em>rises</em>
                {" "}— the work did not shrink, it spread across the spare
                paths in the mesh. Click a block to pin what it is; the full
                tour lives under Inside the fabric.
              </div>
            </div>
          </div>

          <aside className="controls">
            <FabricControls
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
            <FabricCounters
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
