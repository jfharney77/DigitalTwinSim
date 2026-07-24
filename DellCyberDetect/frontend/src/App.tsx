import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchDetect } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { TimelineView } from "./components/TimelineView";
import { DetectControls } from "./components/DetectControls";
import { DetectCounters } from "./components/DetectCounters";
import type { DetectAnatomy, DetectState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "incident" | "anatomy" | "components" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  return "incident";
}

const PAGE_HASH: Record<Page, string> = {
  incident: "",
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

  const [anatomy, setAnatomy] = useState<DetectAnatomy | null>(null);
  const [trace, setTrace] = useState<DetectState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const timer = useRef<number | null>(null);
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
    Promise.all([fetchAnatomy(), fetchDetect()])
      .then(([an, det]) => {
        setAnatomy(an);
        setTrace(det.trace);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const state = trace[cursor] ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (reading every byte of every snapshot) so
      // their real-world cost is visible.
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
        <h1>Dell Cyber Detect</h1>
        <nav className="nav">
          <button
            className={page === "incident" ? "active" : ""}
            onClick={() => setPage("incident")}
          >
            The incident
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the detection
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
        {page === "incident" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedHours}h` : "—"}
          </span>
        )}
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "incident" && (
        <>
          <div className="an-hero">
            <h2>It reads the data, not the metadata</h2>
            <p>
              Almost every ransomware defence watches descriptions of data
              rather than data: did extensions change, did entropy spike,
              was there a mass rename, is the I/O rate unusual. Those are
              cheap to measure, which is exactly why attackers stopped
              triggering them — encrypt slowly, preserve extensions,
              imitate a busy Tuesday, and every one of those detectors
              stays quiet. What cannot be disguised is whether a file still
              means anything. Play the trace and watch four snapshots get
              ruined while the alert counter never leaves zero. Then watch
              what the analysis produces: not an alert, but a{" "}
              <em>date</em>.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <TimelineView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  corruptedCount={state?.snapshotsCorrupted ?? 0}
                  revealed={(state?.contentConfidencePercent ?? 0) > 0}
                  namedClean={state?.lastCleanSnapshot ?? -1}
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
                Pause on the <em>detectors silent</em> step and look at the
                timeline. Every snapshot is drawn identically, because at
                that moment they genuinely are indistinguishable — four of
                them are ruined and nothing visible from outside says
                which. That is the position an administrator is actually
                in. The copies only turn red once the analysis has read the
                bytes inside them, and only then can a marker be placed on
                the last clean one. Click a block to pin what it is; the
                full tour lives under Inside the detection.
              </div>
            </div>
          </div>

          <aside className="controls">
            <DetectControls
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
            <DetectCounters
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
