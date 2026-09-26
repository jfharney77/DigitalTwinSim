import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchNamespace, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ClusterView } from "./components/ClusterView";
import { NamespaceControls } from "./components/NamespaceControls";
import { NamespaceCounters } from "./components/NamespaceCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type { ClusterAnatomy, NamespaceState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "namespace" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "namespace";
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
  namespace: "",
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
    // Only overwrite the hash for top-level switches; pages append their own
    // deep-link segments (#anatomy/<region>, #tour/<step>, #step=N). The
    // namespace page's hash is empty, so check it explicitly.
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) window.location.hash = want;
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<ClusterAnatomy | null>(null);
  const [trace, setTrace] = useState<NamespaceState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  const level = useLevel();

  const traceRef = useRef<NamespaceState[]>([]);
  traceRef.current = trace;
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
    Promise.all([fetchAnatomy(), fetchNamespace()])
      .then(([an, ns]) => {
        setAnatomy(an);
        setTrace(ns.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(ns.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

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
      // Linger on long stages (redistributing data onto the new nodes) so
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
        <h1>Dell PowerScale</h1>
        <nav className="nav">
          <button
            className={page === "namespace" ? "active" : ""}
            onClick={() => setPage("namespace")}
          >
            Namespace in motion
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
        {page === "namespace" && (
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
              // ClusterView draws the map plus a margin and two caption
              // lines: (100 + 5) x (60 + 5 + 6.5).
              stageAspect={(tour.mapWidth + 5) / (tour.mapHeight + 11.5)}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the namespace page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <ClusterView
                  anatomy={anatomy}
                  active={stage.lit}
                  rebalancing={state?.rebalancing ?? false}
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
                      Namespace trace: <strong>{state.label}</strong> · t+
                      {state.elapsedSeconds}s (illustrative)
                      {/* Before the cluster forms there is no file system to
                          count, and the word namespace has not been introduced
                          yet, so the hero counters wait for the first node. */}
                      {state.nodes === 0
                        ? " · cluster not formed yet"
                        : ` · shared file systems (namespaces) ${state.namespaces} · data moves needed (migrations) ${state.migrationsRequired}`}
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

      {page === "namespace" && (
        <>
          <div className="an-hero">
            <h2>There are no volumes</h2>
            {level <= 2 ? (
              <p>
                NAS means network-attached storage: shared folders that many
                computers reach over the network. On most NAS systems someone
                has to divide the space into walled-off sections called
                volumes before anyone knows how much each will need. The
                guess turns out wrong, one volume ends up nearly full while
                another sits empty, and fixing it means a migration (copying
                data from one volume to another) during a maintenance window
                (a planned time when people cannot use the system).
                PowerScale runs software called OneFS that never divides the
                space. One file system covers every storage computer, or
                node, in the group. People reach the same files whether
                their computer speaks NFS, SMB, S3, or HDFS, four common
                ways of asking for files. Growing means adding a node: the
                one shared space, called the namespace, gets bigger while
                data spreads onto the new node in the background. The
                PowerFlex twin makes a similar move for the disk-like
                storage databases use. The Exascale twin covers Lightning, a
                separate, faster file system used as a temporary work area
                beside a cluster like this one.
              </p>
            ) : (
              <p>
                Conventional network-attached storage (NAS) makes you carve
                capacity into fixed volumes before you know what you will
                need. Reality then diverges from the guess, this volume runs
                at 95% while that one sits empty, and moving capacity
                between them means a migration and a maintenance window.
                OneFS, the operating system every PowerScale node runs,
                declines to partition. One file system spans every node in
                the cluster; clients reach the same files over NFS, SMB, S3,
                and HDFS; and growing the system means adding a node, at
                which point the one namespace gets larger while data
                redistributes in the background. The PowerFlex twin next
                door removed the controller; this one removes the volume,
                the same refusal aimed at a different bottleneck. The
                Exascale twin's Lightning file system is a separate product,
                not OneFS: Dell positions it as the scratch tier beside
                PowerScale, which serves the rest of the data's life.
              </p>
            )}
            <button
              className="primary namespace-tour-link"
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
                  rebalancing={state?.rebalancing ?? false}
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
                    Lit blocks are the parts working at this step. The step
                    worth pausing on is <em>addnode</em>, where two more
                    nodes join. Total space jumps, the used share falls,
                    and the count of namespaces (shared file systems) in
                    the telemetry panel stays at 1. The long band across
                    the node row now has two more nodes under it. Most NAS
                    systems would need extra steps here: create a volume,
                    watch it fill, move data out of it. This trace has none
                    of them. Click a block to see what it is. The full
                    guide to the parts is under Inside the cluster.
                  </>
                ) : (
                  <>
                    Highlighted blocks are the parts doing work at this
                    step. The step that repays a pause is <em>addnode</em>:
                    capacity jumps, used percent falls, and the namespace
                    count in the telemetry panel does not move. The single
                    band spanning the node row gets two more nodes under
                    it. A conventional NAS trace would need steps this one
                    refuses to have: provision a volume, watch it fill,
                    migrate. Click a block to pin what it is; the full tour
                    lives under Inside the cluster.
                  </>
                )}
              </div>
            </div>
          </div>

          <aside className="controls">
            <NamespaceControls
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
            <NamespaceCounters
              state={state}
              stepIndex={cursor}
              stepCount={trace.length}
              level={level}
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
