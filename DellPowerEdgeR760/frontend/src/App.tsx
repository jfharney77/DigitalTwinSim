import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchPowerOn, fetchTour } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ChassisView } from "./components/ChassisView";
import { PowerOnControls } from "./components/PowerOnControls";
import { PowerOnCounters } from "./components/PowerOnCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type { ChassisAnatomy, PowerOnState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "poweron" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "poweron";
}

const PAGE_HASH: Record<Page, string> = {
  poweron: "",
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
  cooling: "#122b2b",
  cpu: "#2b2412",
  memory: "#241f33",
  power: "#2b1a1a",
  expansion: "#16281a",
  management: "#12282e",
  board: "#1a2433",
};

const KIND_LABEL: Record<RegionKind, string> = {
  storage: "storage (drives, backplane, RAID)",
  cooling: "cooling (fans, shroud)",
  cpu: "processors",
  memory: "memory (DIMM banks)",
  power: "power delivery",
  expansion: "PCIe expansion",
  management: "management (iDRAC)",
  board: "system board",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<regionId>, #step=N). Comparing
    // pages rather than prefixes matters for the power-on page, whose hash is
    // empty: every hash starts with "#", so a prefix check never cleared a
    // leftover #anatomy and a reload landed back on the wrong page.
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<ChassisAnatomy | null>(null);
  const [trace, setTrace] = useState<PowerOnState[]>([]);
  const [intro, setIntro] = useState("");
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  // Bumped when a #tour/<id> link arrives in an open tab: the player reads
  // its starting step once, at mount, so a new key remounts it there.
  const [tourKey, setTourKey] = useState(0);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply a #step=/#phase= deep link only on the first successful trace load,
  // so a reading-level refetch does not yank the cursor back.
  const hashApplied = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<PowerOnState[]>([]);
  traceRef.current = trace;

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
        setIntro(po.intro ?? "");
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(po.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (the narration is leveled prose).
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
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (memory training, drive spin-up) so their
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

  // Follow the hash after load: in-page links (the use-case page's "Go
  // deeper" buttons), the back button, and a #step=/#phase= link typed into
  // an open tab all change the hash without remounting the app.
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      const tourStep = tourStepFromHash();
      if (tourStep !== null && tourStep !== tourStart.current) {
        tourStart.current = tourStep;
        setTourKey((k) => k + 1);
      }
      const start = initialStepFromHash(traceRef.current);
      if (start !== null) {
        stop();
        setCursor(start);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
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

  // Which step is the longest, by the durations the counter prints. The
  // engine pins memory training as the strict maximum, so the readout can
  // say so on the step itself rather than leaving the reader to compare
  // fifteen numbers by hand (the sibling iDRAC twin labels its own).
  const longestStep = trace.reduce(
    (best, s, i) => {
      const took = s.elapsedSeconds - (trace[i - 1]?.elapsedSeconds ?? 0);
      return took > best.took ? { index: i, took } : best;
    },
    { index: -1, took: -1 },
  ).index;

  return (
    <div className="app dell">
      <header>
        <h1>PowerEdge&nbsp;R760</h1>
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
          <button
            className={page === "tour" ? "active" : ""}
            onClick={() => setPage("tour")}
          >
            Guided tour
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
              stageAspect={2}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the power-on page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <ChassisView
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
                      Power-on trace: <strong>{state.label}</strong> · t+
                      {state.elapsedSeconds}s (illustrative)
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

      {page === "poweron" && (
        <>
          <div className="an-hero">
            <h2>What happens when you plug it in</h2>
            {/* Leveled prose, served with the trace (engine.INTRO). */}
            <p>{intro}</p>
            <button
              className="primary poweron-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
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
              previousElapsedSeconds={
                cursor > 0 ? (trace[cursor - 1]?.elapsedSeconds ?? 0) : 0
              }
              longest={cursor === longestStep}
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
