import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchFabric, fetchScenarios, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { FabricView } from "./components/FabricView";
import { FabricControls } from "./components/FabricControls";
import {
  FabricCounters,
  ecnRowLabel,
  elapsedLabel,
  pfcRowLabel,
} from "./components/FabricCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type { FabricAnatomy, FabricState, RegionKind, Scenario } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "fabric" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "fabric";
}

const PAGE_HASH: Record<Page, string> = {
  fabric: "",
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

// The fabric map is 100 x 62 plus a 2.5-unit margin each side and 4 units of
// orientation labels below, so the diagram box is 105 x 71.
const STAGE_ASPECT = 105 / 71;

// #step=N / #phase=<name> deep-links start playback at a chosen step, and
// #scenario=<id> picks the trace. They compose with "&" in any order
// (#scenario=gray-link&phase=blind). All of them fall through pageFromHash()
// and land on the default page.
const HEALTHY = "healthy";

function simHash(): { scenario: string; step: number | null; phase: string | null } {
  const out = { scenario: HEALTHY, step: null as number | null, phase: null as string | null };
  for (const part of window.location.hash.replace(/^#/, "").split("&")) {
    const m = part.match(/^(scenario|step|phase)=([a-z0-9_-]+)$/i);
    if (!m) continue;
    if (m[1] === "scenario") out.scenario = m[2];
    else if (m[1] === "phase") out.phase = m[2];
    else if (/^\d+$/.test(m[2])) out.step = Number(m[2]);
  }
  return out;
}

function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const { step, phase } = simHash();
  if (step !== null) return Math.min(step, states.length - 1);
  if (phase !== null) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  const tourStart = useRef<string | null>(tourStepFromHash());
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (#anatomy/<regionId>, #tour/<stepId>).
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) window.location.hash = want;
    document.body.classList.add("dell-body");
  }, [page]);
  // Back/forward, hand-edited hashes and in-page links (the use-case "Go
  // deeper" buttons) switch pages too.
  // A #tour/<stepId> link followed inside an open page remounts the player on
  // that step (the player reads its start step once, when it mounts). The
  // player's own step changes use replaceState, which fires no hashchange.
  const [tourKey, setTourKey] = useState(0);
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      const id = tourStepFromHash();
      if (id && id !== tourStart.current) {
        tourStart.current = id;
        setTourKey((k) => k + 1);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const [anatomy, setAnatomy] = useState<FabricAnatomy | null>(null);
  const [trace, setTrace] = useState<FabricState[]>([]);
  // Which trace is playing: the healthy bring-up, or a failure scenario. The
  // hash is the source of truth (the picker only rewrites it), so a scenario
  // is always a shareable link.
  const [scenario, setScenario] = useState<string>(() => simHash().scenario);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
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
    let stale = false;
    Promise.all([fetchAnatomy(), fetchFabric(scenario), fetchScenarios()])
      .then(([an, fb, sc]) => {
        if (stale) return;
        setError(null);
        setAnatomy(an);
        setTrace(fb.trace);
        setScenarios(sc);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const s = initialStepFromHash(fb.trace);
          if (s !== null) setCursor(s);
        }
      })
      .catch((e) => {
        if (stale) return;
        // A scenario id the backend does not know (a mistyped deep link):
        // say so and show the healthy trace, not a dead page.
        if (scenario !== HEALTHY && String(e).includes("404")) {
          setNotice(`There is no scenario called "${scenario}". Showing the healthy bring-up.`);
          setScenario(HEALTHY);
          window.location.hash = "";
          return;
        }
        setError(String(e));
      });
    return () => {
      stale = true;
    };
  }, [level, scenario]);

  // A #step=/#phase=/#scenario= typed into an already-open page moves the
  // cursor too. A scenario change resets the cursor and lets the fetch above
  // apply the rest of the hash against the new trace.
  useEffect(() => {
    const onHash = () => {
      if (pageFromHash() !== "fabric") return;
      const wanted = simHash().scenario;
      if (wanted !== scenario) {
        stop();
        setCursor(0);
        setTrace([]);
        hashApplied.current = false;
        setScenario(wanted);
        return;
      }
      const start = initialStepFromHash(trace);
      if (start !== null) {
        stop();
        setCursor(start);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [trace, scenario, stop]);

  // The guided tour narrates the healthy trace and drives this same cursor.
  useEffect(() => {
    if (page === "tour" && scenario !== HEALTHY) {
      stop();
      setCursor(0);
      setTrace([]);
      setScenario(HEALTHY);
    }
  }, [page, scenario, stop]);

  const pickScenario = useCallback((id: string) => {
    setNotice(null);
    window.location.hash = id === HEALTHY ? "" : `scenario=${id}`;
  }, []);
  const activeScenario = scenarios.find((s) => s.id === scenario) ?? null;
  const failing = scenario !== HEALTHY;

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
          <button
            className={page === "tour" ? "active" : ""}
            onClick={() => setPage("tour")}
          >
            Guided tour
          </button>
        </nav>
        {page === "fabric" && (
          <span className="sub">
            {state ? `${state.label} · ${elapsedLabel(state.elapsedSeconds)}` : "—"}
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
              stageAspect={STAGE_ASPECT}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the fabric page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <FabricView
                  anatomy={anatomy}
                  active={stage.lit}
                  selected={regionId}
                  onSelect={(id) => {
                    setRegionId(id);
                    if (id) stage.onRegionClick(id);
                  }}
                  camera={stage.viewBox}
                  regionLook={stage.regionLook}
                  hot={state}
                />
              )}
              aside={
                <>
                  {state && (
                    <>
                      <p className="tour-trace">
                        Fabric trace: <strong>{state.label}</strong> ·{" "}
                        {elapsedLabel(state.elapsedSeconds)}
                      </p>
                      {/* The counters the narration tells the viewer to
                          watch: the zero that never moves, the link that
                          fills, and what holding the zero costs. */}
                      <dl className="tour-counters">
                        <dt>Dropped packets</dt>
                        <dd>{state.droppedPackets}</dd>
                        <dt>Busiest link</dt>
                        <dd>
                          {state.peakLinkPercent}%
                          {state.peakLinkPercent >= 90 ? ", saturated" : ""}
                        </dd>
                        <dt>Fabric throughput</dt>
                        <dd>{state.fabricTbps} Tb/s</dd>
                        <dt>{ecnRowLabel(level)}</dt>
                        <dd>{state.ecnMarkedPercent}%</dd>
                        <dt>{pfcRowLabel(level)}</dt>
                        <dd>{state.pfcPausesPerSec} /s</dd>
                      </dl>
                      <p className="tour-trace">Values are illustrative.</p>
                    </>
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

      {page === "fabric" && (
        <>
          <div className="an-hero">
            <h2>
              {failing
                ? "A link that fails without going down"
                : "What an AI fabric refuses to do"}
            </h2>
            {/* The intro is scenario data, leveled like the step text. */}
            {activeScenario?.intro && <p>{activeScenario.intro}</p>}
            <button
              className="primary fabric-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {notice && <div className="mini an-error scenario-notice">{notice}</div>}
              {anatomy && (
                <FabricView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  selected={regionId}
                  onSelect={setRegionId}
                  sick={state}
                  hot={state}
                />
              )}
              {state && (
                <div className="poweron-desc">
                  <strong>{state.label}.</strong> {state.description}
                </div>
              )}
              {failing && activeScenario && activeScenario.sources.length > 0 && (
                <div className="mini an-hint scenario-sources">
                  How this failure behaves is drawn from:{" "}
                  {activeScenario.sources.map((src, i) => (
                    <span key={src.url}>
                      {i > 0 ? "; " : ""}
                      <a href={src.url} target="_blank" rel="noreferrer">
                        {src.label}
                      </a>
                    </span>
                  ))}
                  . The same fault is a toggle in the PhysicsFabric simulator.
                </div>
              )}
              {/* This paragraph carries the two numbers the diagram is
                  about, so it is leveled like the step prose beside it,
                  in the vocabulary each register has already set up. */}
              <div className="mini an-hint" hidden={failing}>
                {level <= 2 ? (
                  <>
                    Highlighted blocks are the parts doing work at this step,
                    and the busiest link is drawn in amber while it is full.
                    Watch the congestion step, then the next one, where the
                    fabric moves traffic onto the other route: that link falls
                    from 98% full to 71% while the total data carried rises
                    from 24 to 31 Tb/s. The work did not shrink. It moved onto
                    the path through upper switch 2. Click a block to pin what
                    it is; the full tour lives under Inside the fabric.
                  </>
                ) : level >= 4 ? (
                  <>
                    Highlighted blocks are active this step; the hot link is
                    amber above 90%. Congestion then reroute: 98% → 71% on
                    that link, 24 → 31 Tb/s fabric-wide — the work moved to
                    the spine-2 path, it did not shrink. Click a block to pin
                    it; full tour under Inside the fabric.
                  </>
                ) : (
                  <>
                    Highlighted blocks are the parts doing work at this step,
                    and the busiest link is drawn in amber while it is
                    saturated. Watch the congestion step and then the reroute:
                    that link falls from 98% to 71% while total throughput
                    rises from 24 to 31 Tb/s. The work did not shrink, it
                    moved onto the path through the other spine. Click a block
                    to pin what it is; the full tour lives under Inside the
                    fabric.
                  </>
                )}
              </div>
            </div>
          </div>

          <aside className="controls">
            <FabricControls
              speed={speed}
              running={running}
              done={done}
              phaseLabel={state?.label ?? "—"}
              scenarios={scenarios}
              scenario={scenario}
              onScenario={pickScenario}
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
              failing={failing}
              baselineMs={trace[0]?.collectiveMs ?? 0}
              note={activeScenario?.telemetryNote ?? ""}
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
