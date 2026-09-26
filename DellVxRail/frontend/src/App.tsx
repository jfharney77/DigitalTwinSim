import { useCallback, useEffect, useRef, useState } from "react";
import {
  HAPPY_SCENARIO,
  fetchAnatomy,
  fetchFirstRun,
  fetchScenarios,
  fetchTour,
} from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ClusterView } from "./components/ClusterView";
import { FirstRunControls } from "./components/FirstRunControls";
import { FirstRunCounters, clockLabel } from "./components/FirstRunCounters";
import { LevelControl } from "./components/LevelControl";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { useLevel } from "./level";
import type {
  ClusterAnatomy,
  FirstRunState,
  RegionKind,
  ScenarioInfo,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "firstrun" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "firstrun";
}

// Deep-link into the trace: #step=N (clamped) or #phase=<name> (first
// matching state). Returns null when the hash names neither.
//
// Both compose with a scenario: #scenario=node-add-mismatch&phase=refused.
// The hash is read as key=value pairs joined by "&"; a page hash such as
// #anatomy has no "=" and yields no parameters.
function hashParams(): URLSearchParams {
  const h = window.location.hash.replace(/^#/, "");
  return new URLSearchParams(h.includes("=") ? h : "");
}

function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const params = hashParams();
  const step = params.get("step");
  if (step !== null && /^\d+$/.test(step)) {
    return Math.min(Number(step), states.length - 1);
  }
  const phase = params.get("phase");
  if (phase !== null) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

// Which trace the sim page plays: #scenario=<id>. Absent means the first
// run. An unknown id is kept as typed; the backend answers 404 and the page
// shows the error instead of quietly playing something else.
function scenarioFromHash(): string {
  const id = hashParams().get("scenario");
  return id && /^[a-z0-9-]+$/i.test(id) ? id : HAPPY_SCENARIO;
}

const PAGE_HASH: Record<Page, string> = {
  firstrun: "",
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
    // Rewrite the hash only when it names a different page, so a
    // #step=/#phase= deep link on the first-run page survives. (Comparing
    // with startsWith against the first-run page's empty hash matched every
    // hash, so switching back to First run left #usecases/... in the URL.)
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);
  // Back/forward, hand-edited hashes, and in-page links (the use-case
  // page's "Go deeper" buttons) switch pages too.
  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const [anatomy, setAnatomy] = useState<ClusterAnatomy | null>(null);
  const [trace, setTrace] = useState<FirstRunState[]>([]);
  const [scenario, setScenario] = useState<string>(scenarioFromHash);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
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
  // A scenario change refetches too (the node-add scenario has its own,
  // taller map), and re-arms the deep link so that
  // #scenario=<id>&phase=<name> lands on that phase of the new trace.
  useEffect(() => {
    let stale = false;
    Promise.all([
      fetchAnatomy(scenario),
      fetchFirstRun(scenario),
      fetchScenarios(),
    ])
      .then(([an, fr, sc]) => {
        if (stale) return;
        setError(null);
        setAnatomy(an);
        setTrace(fr.trace);
        setScenarios(sc);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(fr.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => {
        if (stale) return;
        const message = e instanceof Error ? e.message : String(e);
        // A mistyped #scenario= is not an outage: play the first run instead
        // of leaving an empty page.
        if (scenario !== HAPPY_SCENARIO && /404|Unknown scenario/.test(message)) {
          window.history.replaceState(
            null,
            "",
            window.location.pathname + window.location.search,
          );
          setScenario(HAPPY_SCENARIO);
          return;
        }
        setTrace([]);
        setError(message);
      });
    return () => {
      stale = true;
    };
  }, [level, scenario]);

  // Pick a scenario: stop, rewind, and put the choice in the URL. The cursor
  // always resets, because step N of one trace is not step N of another.
  const chooseScenario = useCallback(
    (id: string) => {
      if (id === scenarioRef.current) return;
      stop();
      setCursor(0);
      setRegionId(null);
      hashApplied.current = true; // a picked scenario starts at its first step
      window.history.replaceState(
        null,
        "",
        id === HAPPY_SCENARIO
          ? window.location.pathname + window.location.search
          : `#scenario=${id}`,
      );
      setScenario(id);
    },
    [stop],
  );

  // The guided tour narrates the first run on the four-node map and drives
  // this same cursor, so opening it puts the first run back under it.
  useEffect(() => {
    if (page === "tour" && scenarioRef.current !== HAPPY_SCENARIO) {
      stop();
      setCursor(0);
      setScenario(HAPPY_SCENARIO);
    }
  }, [page, stop]);

  // A #scenario=/#step=/#phase= typed into an already-open page moves the
  // app too, not just the URL.
  useEffect(() => {
    const onHash = () => {
      if (pageFromHash() !== "firstrun") return;
      const wanted = scenarioFromHash();
      if (wanted !== scenarioRef.current) {
        // A different trace: rewind now, and let the fetch apply any
        // &phase= / &step= once the new trace has arrived.
        stop();
        setCursor(0);
        setRegionId(null);
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
  }, [trace, stop]);

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
      // Linger on long stages (ESXi boot, cluster build) so their real-world
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

  const scenarioInfo = scenarios.find((s) => s.id === scenario) ?? null;
  const isFailure = scenario !== HAPPY_SCENARIO;

  const selectedRegion =
    anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <div className="app dell">
      <header>
        <h1>VxRail</h1>
        <nav className="nav">
          <button
            className={page === "firstrun" ? "active" : ""}
            onClick={() => setPage("firstrun")}
          >
            First run
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the cluster
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
        {page === "firstrun" && (
          <span className="sub">
            {state ? `${state.label} · ${clockLabel(state.elapsedSeconds)}` : "—"}
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
          {tour && anatomy && !isFailure && anatomy.height === tour.mapHeight && (
            <TourPlayer
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              // ClusterView draws a margin and orientation labels around the
              // map: (100 + 5) x (64 + 5 + 4).
              stageAspect={105 / 73}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the first-run page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <ClusterView
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
                      First-run trace: <strong>{state.label}</strong> · t+
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

      {page === "firstrun" && (
        <>
          <div className="an-hero">
            <h2>
              {isFailure
                ? "What happens when a node add is refused"
                : "What happens on a cluster's first run"}
            </h2>
            {isFailure ? (
              <p>
                Months after the first run, the cluster needs capacity and a
                fifth node arrives. Its factory image is older than the
                cluster, which was upgraded in the meantime. VxRail Manager
                checks the version before it changes anything, so the add is
                refused while the node is still a stranger to vSAN (the
                software that pools the nodes' drives). The admin re-images
                the node, the retry passes, and vSAN rebalances across five.
                Watch the four original nodes: they stay lit on every step.
              </p>
            ) : level <= 2 ? (
              <p>
                A VxRail cluster is not one computer starting up. It is
                several identical servers, called nodes, joining into one
                system. Each node first loads software that lets one real
                server run many pretend computers, called virtual machines.
                The nodes then find each other over the network and pick one
                of themselves to lead. The leader runs VxRail Manager, the
                program that joins the nodes into one cluster and pools the
                fast flash drives inside every node into one shared store of
                data. Play the trace and watch each stage light up the
                hardware it runs on.
              </p>
            ) : level >= 4 ? (
              <p>
                Four nodes boot ESXi in lockstep, discover each other, and
                elect a primary that runs VxRail Manager. It builds the
                vSphere cluster and claims every node's NVMe into one vSAN
                datastore. Play the trace to see which hardware each stage
                uses.
              </p>
            ) : (
              <p>
                A VxRail cluster is not one machine booting. It is several
                identical nodes fusing into one hyperconverged system, where
                compute, storage and virtualization share the same servers.
                Power them on together and each boots VMware ESXi, the
                hypervisor that runs virtual machines. The nodes find each
                other over the network and elect a primary node that runs
                VxRail Manager. That node builds the vSphere cluster and
                pools every node's local NVMe drives into one shared vSAN
                datastore. Play the trace and watch each stage light up the
                hardware it runs on.
              </p>
            )}
            <button
              className="primary firstrun-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <ClusterView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  failed={new Set(state?.failedRegions ?? [])}
                  selected={regionId}
                  onSelect={setRegionId}
                />
              )}
              {state && (
                <div className="poweron-desc">
                  <strong>{state.label}.</strong> {state.description}
                </div>
              )}
              {isFailure ? (
                <div className="mini an-hint">
                  Highlighted blocks are the parts doing work at this step.
                  Blocks with a dashed red outline belong to the refused node.
                  The fifth node is the bottom row; its NVMe stays dark until
                  the second check has passed. Click a block to pin what it
                  is.
                </div>
              ) : (
                <div className="mini an-hint">
                  Highlighted blocks are the parts doing work at this step.
                  Watch the nodes move in lockstep — until the primary
                  election, when exactly one node lights up to run VxRail
                  Manager. Click a block to pin what it is; every block is
                  described under Inside the cluster.
                </div>
              )}
              {isFailure && scenarioInfo && (
                <div className="mini scenario-note">
                  <p>
                    How the refusal, the re-image and discovery behave follows
                    the sources below. The version pair, terabytes, VM count,
                    watts and timings are illustrative.
                  </p>
                  <div className="an-sources">
                    {scenarioInfo.sources.map((src) => (
                      <a
                        key={src.url}
                        href={src.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {src.label}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <aside className="controls">
            <FirstRunControls
              scenario={scenario}
              scenarios={scenarios}
              onScenario={chooseScenario}
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
            <FirstRunCounters
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
