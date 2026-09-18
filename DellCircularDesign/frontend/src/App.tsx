import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchLifecycle, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { LoopView } from "./components/LoopView";
import { LifecycleControls } from "./components/LifecycleControls";
import {
  LifecycleCounters,
  PHASE_LABEL,
  fmtElapsed,
} from "./components/LifecycleCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type { LifecycleMap, MaterialState, RegionKind } from "./types";

// LoopView draws the 100 x 70 map inside a 2.5-unit margin with two caption
// lines below it: 105 x 81.4. The tour stage keeps that shape.
const LOOP_ASPECT = 105 / 81.4;

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "lifecycle" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "lifecycle";
}

// Deep-link into the trace: #step=N (clamped) or #phase=<name> (first
// matching state). Returns null when the hash names neither.
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

const PAGE_HASH: Record<Page, string> = {
  lifecycle: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
  tour: "tour",
};

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
}

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Compare the page the hash names, not a prefix: every hash starts with
    // "#", so a prefix test let #usecases/... survive a switch back to the
    // lifecycle page, and a reload then reopened the wrong page.
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  // Follow in-page hash edits too (a pasted #phase= link, back/forward):
  // switch page, and re-seek the cursor when the hash names a step.
  const [hashSeek, setHashSeek] = useState(0);
  // A #tour/<id> edited in place (pasted link, back/forward) remounts the
  // player on that beat; otherwise the URL would name one beat while the
  // stage showed another. The player's own step changes use replaceState,
  // which fires no hashchange, so this never loops.
  const [tourKey, setTourKey] = useState(0);
  const tourStart = useRef<string | null>(tourStepFromHash());
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      setHashSeek((n) => n + 1);
      const id = tourStepFromHash();
      if (id && id !== tourStart.current) {
        tourStart.current = id;
        setTourKey((k) => k + 1);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const [anatomy, setAnatomy] = useState<LifecycleMap | null>(null);
  const [trace, setTrace] = useState<MaterialState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
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

  useEffect(() => {
    if (hashSeek === 0 || trace.length === 0) return;
    const start = initialStepFromHash(trace);
    if (start !== null) {
      stop();
      setCursor(start);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hashSeek]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (the narration is leveled server-side).
  const tourWanted = page === "tour" || tour !== null;
  useEffect(() => {
    if (!tourWanted) return;
    fetchTour()
      .then(setTour)
      .catch((e) => setTourError(String(e)));
  }, [level, tourWanted]);

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
          <button
            className={page === "tour" ? "active" : ""}
            onClick={() => setPage("tour")}
          >
            Guided tour
          </button>
        </nav>
        {page === "lifecycle" && (
          <span className="sub">
            {/* The short phase name: the full step title is on the card
                below, and here it wrapped the whole header. */}
            {state
              ? `${PHASE_LABEL[state.phase]} · t+${fmtElapsed(state.elapsedMonths)}`
              : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "tour" && (
        <div className="tour-page">
          {(tourError || error) && (
            <div className="mini an-error">{tourError ?? error}</div>
          )}
          {tour && anatomy && (
            <TourPlayer
              key={tourKey}
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              stageAspect={LOOP_ASPECT}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the lifecycle page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <LoopView
                  anatomy={anatomy}
                  active={stage.lit}
                  selected={regionId}
                  onSelect={(id) => {
                    setRegionId(id);
                    if (id) stage.onRegionClick(id);
                  }}
                  camera={stage.viewBox}
                  regionLook={stage.regionLook}
                />
              )}
              aside={
                <>
                  {state && (
                    <p className="tour-trace">
                      Material trace: <strong>{state.label}</strong> · t+
                      {fmtElapsed(state.elapsedMonths)} (illustrative)
                    </p>
                  )}
                  {selectedRegion && (
                    <div>
                      <h2>{selectedRegion.label}</h2>
                      <p className="tour-trace">{selectedRegion.description}</p>
                    </div>
                  )}
                </>
              }
            />
          )}
        </div>
      )}

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
            <button
              className="primary lifecycle-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
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
