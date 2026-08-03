import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchLifecycle } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { LoopView } from "./components/LoopView";
import { LifecycleControls } from "./components/LifecycleControls";
import {
  LifecycleCounters,
  fmtElapsed,
} from "./components/LifecycleCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type { LifecycleMap, MaterialState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "lifecycle" | "anatomy" | "components" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  return "lifecycle";
}

// Deep-link into the trace: #step=N (clamped) or #phase=<name> (first
// matching state). Returns null when the hash names neither.
function initialStepFromHash(states: { phase: string }[]): number | null {
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

const PAGE_HASH: Record<Page, string> = {
  lifecycle: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    if (!window.location.hash.startsWith(`#${PAGE_HASH[page]}`)) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<LifecycleMap | null>(null);
  const [trace, setTrace] = useState<MaterialState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  // Apply a #step=/#phase= deep link only on the first successful load — a
  // reading-level refetch must not yank the cursor back.
  const hashApplied = useRef(false);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
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
    Promise.all([fetchAnatomy(), fetchLifecycle()])
      .then(([an, lc]) => {
        setAnatomy(an);
        setTrace(lc.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(lc.trace);
          if (start !== null) setCursor(start);
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
      // Linger on long stages (manufacture, above all) so their real-world
      // cost is visible.
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
        <h1>Dell Circular Design</h1>
        <nav className="nav">
          <button
            className={page === "lifecycle" ? "active" : ""}
            onClick={() => setPage("lifecycle")}
          >
            One device, one loop
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            The loop itself
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
        {page === "lifecycle" && (
          <span className="sub">
            {state ? `${state.label} · t+${fmtElapsed(state.elapsedMonths)}` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "lifecycle" && (
        <>
          <div className="an-hero">
            <h2>The trace that closes</h2>
            <p>
              Every other twin in this repository ends at steady: the server
              reaches os, the fabric reaches steady, the rack reaches ready
              — as if working forever were what machines do. They don't.
              Every one of them will be decommissioned, and what happens
              next is either landfill or the material input to the next
              generation. This trace follows one laptop cohort all the way
              around: recycled cobalt, copper, steel and plastics in;
              manufacture; years of service stretched by repair; take-back;
              and a sort into reused, reclaimed, and honestly lost. The
              conservation rule is borrowed from the IR7000 cooling twin —
              that one insists heat does not vanish, this one insists mass
              does not — and the devices whose afterlife it models are the
              clients next door, the Pro Max Plus and the Alienware. The
              biggest lever is none of the recycling machinery: it is the
              repair steps in the middle, because a year more of service
              defers an entire manufacturing cycle.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <LoopView
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
                Highlighted blocks are where the material is at this step.
                Watch the loop close: the final step lights the materials
                block again, and the recycled-input percentage in the ledger
                reads higher than it did at step one — the output of this
                cycle is the input of the next. Keep an eye on the dashed
                red edge too; some mass takes it, and the ledger says
                exactly how much. Click a block to pin what it is; the full
                tour lives under The loop itself.
              </div>
            </div>
          </div>

          <aside className="controls">
            <LifecycleControls
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
            <LifecycleCounters
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
