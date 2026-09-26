import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchCluster, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ClusterView } from "./components/ClusterView";
import { ClusterControls } from "./components/ClusterControls";
import { ClusterCounters } from "./components/ClusterCounters";
import { LevelControl } from "./components/LevelControl";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { useLevel } from "./level";
import type { ClusterAnatomy, ClusterState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "pool" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "pool";
}

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
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
  pool: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
  tour: "tour",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Compare pages, not prefixes: the pool page's hash is empty and every
    // hash starts with "#", so a prefix check never cleared a leftover
    // #anatomy. Pages may append their own segments (#anatomy/<id>, #step=N).
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<ClusterAnatomy | null>(null);
  const [trace, setTrace] = useState<ClusterState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  // Bumped when a #tour/<id> link arrives in an already-open tab, so the
  // player remounts on that beat (it reads initialStepId once).
  const [tourMount, setTourMount] = useState(0);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  // Apply a #step=/#phase= deep link only on the first successful load — a
  // reading-level refetch must not yank the cursor back.
  const hashApplied = useRef(false);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<ClusterState[]>([]);
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
    Promise.all([fetchAnatomy(), fetchCluster()])
      .then(([an, cl]) => {
        setAnatomy(an);
        setTrace(cl.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(cl.trace);
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
  // Nodes the trace has lost: dark while the rest of the pool is online.
  const nodeIds = anatomy?.regions.filter((r) => r.kind === "node").map((r) => r.id) ?? [];
  const lostNodes = new Set(
    state && state.nodesOnline > 0 && state.nodesOnline < nodeIds.length
      ? nodeIds.filter((id) => !state.activeRegions.includes(id))
      : [],
  );

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (scattering chunks across every node) so
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

  // Follow the hash after load: in-page links (the use-case page's "Go
  // deeper" buttons), the back button, and a #step=/#phase= link typed into
  // an open tab all change the hash without remounting the app.
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      const beat = tourStepFromHash();
      if (beat !== null && beat !== tourStart.current) {
        tourStart.current = beat;
        setTourMount((n) => n + 1);
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

  return (
    <div className="app dell">
      <header>
        <h1>Dell PowerFlex</h1>
        <nav className="nav">
          <button
            className={page === "pool" ? "active" : ""}
            onClick={() => setPage("pool")}
          >
            Pool in motion
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the pool
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
        {page === "pool" && (
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
              key={tourMount}
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              // ClusterView draws a margin and a label row around the map.
              stageAspect={(tour.mapWidth + 5) / (tour.mapHeight + 9)}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the pool page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <ClusterView
                  anatomy={anatomy}
                  active={stage.lit}
                  rebuilding={(state?.rebuildParticipants ?? 0) > 0}
                  selected={regionId}
                  onSelect={(id) => {
                    setRegionId(id);
                    if (id) stage.onRegionClick(id);
                  }}
                  camera={stage.viewBox}
                  regionLook={(id) => {
                    // A node the trace has lost stays ghosted even when the
                    // beat restores the outer layer: the pool is one short.
                    const look = stage.regionLook(id);
                    return lostNodes.has(id)
                      ? { ...look, opacity: Math.min(look.opacity, 0.3) }
                      : look;
                  }}
                />
              )}
              aside={
                <>
                  {state && (
                    <p className="tour-trace">
                      Cluster trace: <strong>{state.label}</strong> · t+
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

      {page === "pool" && (
        <>
          <div className="an-hero">
            <h2>There is no controller</h2>
            {level <= 2 ? (
              <p>
                Most shared storage is built around controllers: special
                computers that every piece of data has to pass through.
                PowerStore and PowerMax, shown elsewhere in this collection,
                work that way, and much of their engineering goes into
                surviving a controller failure by switching work to a
                partner, called a failover, which applications feel as a
                pause. PowerFlex removes the centre instead. Ordinary
                servers contribute their own drives, the data is cut into
                small pieces called chunks and spread across all of them,
                and the computers using the storage read straight from the
                servers holding what they want. Play the trace to the
                failure step and watch what a lost server costs: speed falls
                by that server's share, one sixth, nothing switches over to
                a partner, and <em>every</em> surviving server rebuilds a
                small part of what was lost at the same time. Recovery gets
                faster as the pool grows.
              </p>
            ) : level >= 4 ? (
              <p>
                No controller tier. Chunks are mirrored across every node
                and clients address the nodes directly. A node loss costs
                1/n of throughput with no controller failover, and the
                rebuild is many-to-many across <em>every</em> survivor, so
                rebuild time falls as the pool grows.
              </p>
            ) : (
              <p>
                PowerStore and PowerMax, both twinned elsewhere here, are
                built around controllers that every byte passes through,
                and most of their engineering goes into making that
                centrality survivable. PowerFlex removes the centre instead.
                Servers contribute local drives, volumes are chopped into
                chunks scattered across all of them, and clients read
                straight from the nodes holding what they want. Play the
                trace to the failure step and watch what a lost server
                costs: a dip of one sixth, the missing node's share, no
                controller failover, and a rebuild in which <em>every</em>
                {" "}surviving node reconstructs a sliver at once. Recovery
                gets faster as the pool grows.
              </p>
            )}
            <button
              className="primary pool-tour-link"
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
                  rebuilding={(state?.rebuildParticipants ?? 0) > 0}
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
                {level <= 2 ? (
                  <>
                    Highlighted blocks are the parts doing work at this
                    step. Two moments repay a pause. At <em>steady I/O</em>
                    {" "}(I/O is input/output: clients reading and writing),
                    the metadata manager is dark. It gave each client the
                    chunk map, the list of which server holds which piece,
                    and stepped out of the way, so no request passes through
                    it. At <em>rebuild</em>, a web of lines appears between
                    the servers: every survivor linked to every other, each
                    rebuilding a fifth of what was lost. In a controller
                    array, storage built around one pair of controllers, all
                    of that repair traffic would run through the one pair.
                    Click a block to pin what it is; the full tour lives
                    under Inside the pool.
                  </>
                ) : level >= 4 ? (
                  <>
                    Lit blocks are active at this step. The metadata manager
                    is dark at <em>steady I/O</em>; the node-to-node mesh
                    appears only during <em>rebuild</em>. Click a block to
                    pin it.
                  </>
                ) : (
                  <>
                    Highlighted blocks are the parts doing work at this
                    step. Two moments repay a pause. At <em>steady I/O</em>,
                    notice the metadata manager is dark: it handed out the
                    chunk map and stepped out of the way, so no request
                    passes through it. At <em>rebuild</em>, a second mesh
                    appears: every surviving node linked to every other,
                    each reconstructing a fifth of what was lost. In a
                    controller array all of that traffic would run through
                    one controller pair. Click a block to pin what it is;
                    the full tour lives under Inside the pool.
                  </>
                )}
              </div>
            </div>
          </div>

          <aside className="controls">
            <ClusterControls
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
            <ClusterCounters
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
