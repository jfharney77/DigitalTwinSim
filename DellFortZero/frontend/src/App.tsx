import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAccess, fetchAnatomy, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { PillarView } from "./components/PillarView";
import { AccessControls } from "./components/AccessControls";
import { AccessCounters } from "./components/AccessCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type { AccessState, RegionKind, ZeroTrustMap } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)
// PillarView's outline margin, in map units; the tour stage keeps its ratio.
const TOUR_MARGIN = 2.5;

type Page = "access" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "access";
}

const PAGE_HASH: Record<Page, string> = {
  access: "",
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

// Deep-link a trace step: /#step=N (clamped) or /#phase=<name> (first step of
// that phase). Unknown hashes and phases are a no-op; page hashes above are
// unaffected since neither pattern matches a page prefix.
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

// The landing paragraph in three registers, picked by the reading level.
// It leads with the perimeter model's failure; the pointers to the other
// twins come last, because a course reader may not have met them yet.
const HERO_INTRO = {
  novice:
    "Security used to mean a wall. Check people at the gate, then trust " +
    "whatever is already inside. Access given just for being inside has a " +
    "name: implicit trust. Its weakness is that an attacker who gets in " +
    "once is handed that same trust. Zero trust does not build a stronger " +
    "wall, it removes the idea of an inside. Every request for every " +
    "single thing is checked on its own evidence. Play the trace to the " +
    "breach step and look at what an attacker sitting inside the office " +
    "network can reach. Nothing, and not because a guard stopped the " +
    "attack: being inside was never worth anything.",
  standard:
    "Security was built around a perimeter: verify at the boundary, then " +
    "trust what is behind it. The recurring failure of that model is that " +
    "an attacker who gets in once inherits what the inside was allowed to " +
    "do. Zero trust does not harden the perimeter, it deletes the concept. " +
    "Play the trace to the breach step and watch what an attacker with a " +
    "valid position inside the network can reach. Nothing, and not because " +
    "the attack was blocked: being inside was never worth anything. The " +
    "trace stages that breach with network position only, no live session " +
    "and no token; the breach step says what a hijacked live session would " +
    "be bounded to. Most other twins in this repo carry their lesson in a " +
    "boundary, such as the PowerProtect air gap. This one carries it in " +
    "the absence of one.",
  expert:
    "Perimeter model: verify at the boundary, trust the interior, so " +
    "initial access inherits the interior's permissions. Zero trust " +
    "removes the interior. The breach step tests network position only " +
    "(no session, no token): reachable 0, implicit trust grants 0.",
} as const;

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Compare pages rather than prefixes: the access page's hash is empty and
    // every hash starts with "#", so a prefix check never cleared a leftover
    // #anatomy and a reload landed back on the wrong page. Pages may append
    // their own segments (#anatomy/<id>, #usecases/<id>, #step=N).
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<ZeroTrustMap | null>(null);
  const [trace, setTrace] = useState<AccessState[]>([]);
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
  const hashApplied = useRef(false); // deep-link applies once, not on level refetch
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<AccessState[]>([]);
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
    Promise.all([fetchAnatomy(), fetchAccess()])
      .then(([an, acc]) => {
        setAnatomy(an);
        setTrace(acc.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const s = initialStepFromHash(acc.trace);
          if (s !== null) setCursor(s);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (its narration is leveled server-side).
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
      // Linger on long stages (continuous verification) so their
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

  const breached =
    state !== null && (state.phase === "breach" || state.phase === "contained");

  return (
    <div className="app dell">
      <header>
        <h1>Project Fort Zero</h1>
        <nav className="nav">
          <button
            className={page === "access" ? "active" : ""}
            onClick={() => setPage("access")}
          >
            One request
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the architecture
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
        {page === "access" && (
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
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              stageAspect={
                (tour.mapWidth + 2 * TOUR_MARGIN) /
                (tour.mapHeight + 2 * TOUR_MARGIN + 4)
              }
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the access page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <PillarView
                  anatomy={anatomy}
                  active={stage.lit}
                  breached={breached}
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
                      Access trace: <strong>{state.label}</strong> · resources
                      reachable {state.resourcesReachable} · t+
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

      {page === "access" && (
        <>
          <div className="an-hero">
            <h2>There is no inside</h2>
            <p>{HERO_INTRO[level <= 2 ? "novice" : level >= 5 ? "expert" : "standard"]}</p>
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
                <PillarView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  breached={breached}
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
                Highlighted pillars feed the decision at this step; lit
                spokes show the policy engine drawing on them. Two moments
                repay a pause. At <em>context</em>, network location is
                gathered and grants nothing — resources reachable is still
                zero, where a perimeter model would already have said yes.
                At <em>decide</em>, every spoke lights at once: the
                reference architecture is not a menu, and a gap in any
                pillar is a route around all of them. Click a pillar to pin
                what it is; the full tour lives under Inside the
                architecture.
              </div>
            </div>
          </div>

          <aside className="controls">
            <AccessControls
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
            <AccessCounters
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
                <h2>Pillars</h2>
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
