import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchDetect, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { TimelineView } from "./components/TimelineView";
import { DetectControls } from "./components/DetectControls";
import { DetectCounters } from "./components/DetectCounters";
import { LevelControl } from "./components/LevelControl";
import { emph } from "./components/Emph";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type { DetectAnatomy, DetectState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "incident" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "incident";
}

const PAGE_HASH: Record<Page, string> = {
  incident: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
  tour: "tour",
};

// The map draws a margin and orientation labels around the 100 x 58 map, so
// the stage box is (100 + 5) x (58 + 5 + 4).
const TOUR_STAGE_ASPECT = 105 / 67;

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
}

// #step=N / #phase=<name> deep-links start playback at a chosen step; both
// fall through pageFromHash() and land on the default page.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
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
    // Compare pages, not prefixes: the incident page's hash is empty and
    // every hash starts with "#", so a prefix check never cleared a leftover
    // #anatomy. Pages may append their own segments (#anatomy/<id>,
    // #usecases/<id>, #step=N, #phase=<name>).
    if (pageFromHash() !== page) {
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
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply the #step=/#phase= deep-link only on the first load — a
  // reading-level refetch must not yank the cursor back.
  const hashApplied = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<DetectState[]>([]);
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
    Promise.all([fetchAnatomy(), fetchDetect()])
      .then(([an, det]) => {
        setAnatomy(an);
        setTrace(det.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const s = initialStepFromHash(det.trace);
          if (s !== null) setCursor(s);
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

  // Follow the hash after load: the use-case page's "Go deeper" buttons,
  // the back button, and a #step=/#phase= link typed into an open tab all
  // change the hash without remounting the app.
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
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
  const snapshotLabels = (anatomy?.regions ?? [])
    .filter((r) => r.kind === "snapshot")
    .sort((a, b) => a.x - b.x)
    .map((r) => r.label);
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
          <button
            className={page === "tour" ? "active" : ""}
            onClick={() => setPage("tour")}
          >
            Guided tour
          </button>
        </nav>
        {page === "incident" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedHours}h` : "—"}
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
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              stageAspect={TOUR_STAGE_ASPECT}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the incident page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                // Corruption is still drawn only once content analysis has
                // run: the tour pins the cursor, and `revealed` follows it.
                <TimelineView
                  anatomy={anatomy}
                  active={stage.lit}
                  corruptedCount={state?.snapshotsCorrupted ?? 0}
                  revealed={(state?.contentConfidencePercent ?? 0) > 0}
                  namedClean={state?.lastCleanSnapshot ?? -1}
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
                      Incident trace: <strong>{state.label}</strong> · t+
                      {state.elapsedHours}h (illustrative) · metadata alerts{" "}
                      {state.metadataAlerts}
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
                  <strong>{state.label}.</strong> {emph(state.description)}
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
              snapshotLabels={snapshotLabels}
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
