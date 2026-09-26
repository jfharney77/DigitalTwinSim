import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchFabric, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { FabricView } from "./components/FabricView";
import { FabricControls } from "./components/FabricControls";
import { FabricCounters } from "./components/FabricCounters";
import { LevelControl } from "./components/LevelControl";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { useLevel } from "./level";
import type { FabricAnatomy, FabricState, RegionKind } from "./types";

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
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<regionId>), and the fabric page
    // keeps #step=/#phase= links.
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) window.location.hash = want;
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<FabricAnatomy | null>(null);
  const [trace, setTrace] = useState<FabricState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  const [tourKey, setTourKey] = useState(0);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply the #step=/#phase= deep-link only on the first load — a
  // reading-level refetch must not yank the cursor back.
  const hashApplied = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<FabricState[]>([]);
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
    Promise.all([fetchAnatomy(), fetchFabric()])
      .then(([an, fb]) => {
        setAnatomy(an);
        setTrace(fb.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const s = initialStepFromHash(fb.trace);
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

  // Follow the hash after load: in-page links (the use-case page's "Go
  // deeper" buttons), the back button, and a #step=/#phase= link typed into
  // an open tab all change the hash without remounting the app.
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      // A #tour/<id> typed into an open tab (the player only reads its
      // start step at mount): remount the player on that beat.
      const beat = tourStepFromHash();
      if (beat !== null && beat !== tourStart.current) {
        tourStart.current = beat;
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

  return (
    <div className="app dell">
      <header>
        <h1>Quantum-X800 InfiniBand</h1>
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
              // FabricView draws a margin and a line of orientation labels
              // around the map: (100 + 5) x (64 + 5 + 4).
              stageAspect={105 / 73}
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
                />
              )}
              aside={
                <>
                  {state && (
                    <>
                      <p className="tour-trace">
                        Fabric trace: <strong>{state.label}</strong> · t+
                        {state.elapsedSeconds}s
                      </p>
                      {/* The counters the narration tells the viewer to
                          watch: the SHARP crossing, the burst's stall, and
                          the zero that never moves. Illustrative values. */}
                      <dl className="tour-counters">
                        <dt>Sent without credit</dt>
                        <dd>{state.packetsSentWithoutCredit}</dd>
                        <dt>Sender stall</dt>
                        <dd>{state.stallMicrosPerSec.toLocaleString()} µs/s</dd>
                        <dt>Fabric traffic</dt>
                        <dd>{state.fabricTbps} Tb/s</dd>
                        <dt>Effective all-reduce</dt>
                        <dd>
                          {state.allreduceGbps.toLocaleString()} Gb/s (
                          {(state.allreduceGbps / 1000).toFixed(1)} Tb/s)
                        </dd>
                        <dt>Busiest link</dt>
                        <dd>{state.peakLinkPercent}%</dd>
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
              {level <= 2
                ? "A network that cannot lose data"
                : "Lossless by construction, not by vigilance"}
            </h2>
            {level <= 2 ? (
              <p>
                This page plays a network for a GPU cluster coming to life,
                one step at a time. The network is InfiniBand, a kind built
                for supercomputers. An ordinary network (Ethernet, like the
                SN6000 twin) throws data away when a cable gets too full,
                so it has to react quickly to avoid that. InfiniBand works
                the other way round: a sender may not send anything until
                the receiver has promised it room. That promise is called
                a credit, so nothing is ever sent without a place to land.
                Three things to watch. First, one small computer called the
                subnet manager (the block labelled Manager; NVIDIA's
                software for it is called UFM) maps the network and writes
                every route into the switches before any data moves, then
                steps aside. Second, a feature called SHARP lets the
                switches add up the GPUs' numbers as they pass through,
                instead of only carrying them. Third, when many senders
                aim at one receiver at once (an incast burst), the senders
                wait a moment instead of losing anything. The TACC Horizon
                supercomputer in Texas uses this kind of network. Play the
                steps and watch the sent-without-credit counter. It stays
                at zero.
              </p>
            ) : level >= 4 ? (
              <p>
                Ethernet (the SN6000 twin) is lossless only as a reaction
                executed in time. InfiniBand is lossless by construction:
                no transmit without granted buffer credits, so uncredited
                tx = 0 on every step, unexpressible at the link layer. The
                SM programs routes up front and is active in{" "}
                {"{discover, routes}"} only — absent from every traffic
                step. At the SHARP step the counters cross: fabric traffic
                falls, effective all-reduce rises, because the reduction
                runs in the switches. The incast burst drives the hot link
                past 95% and is paid in sender stalls, not loss. The
                fabric TACC's Horizon names.
              </p>
            ) : (
              <p>
                The Ethernet fabric twin (SN6000) must prove it never drops a
                packet — Ethernet drops by default, so losslessness there is
                a reaction executed in time. InfiniBand inverts the premise:
                a sender may not transmit until the receiver has granted it
                buffer credits, so a packet is never sent without a reserved
                place to land. One central subnet manager (the block
                labelled UFM / SM: NVIDIA's Unified Fabric Manager running
                the subnet manager) maps the fabric and programs every route
                before a byte moves, then steps aside; SHARP puts the
                all-reduce arithmetic (summing every GPU's gradients) in
                the switches themselves; and under the incast burst, many
                senders converging on one receiver, senders wait
                microseconds instead of losing anything. This is the fabric
                TACC's Horizon names. Play the trace and watch the
                sent-without-credit counter — it cannot move.
              </p>
            )}
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
              {anatomy && (
                <FabricView
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
                {level <= 2 ? (
                  <>
                    Highlighted blocks are the parts doing work at this
                    step. Watch the Manager block (the subnet manager): it
                    lights only while it maps the network and writes the
                    routes, and stays dark after that, because data never
                    passes through it. Then watch the SHARP step, where
                    fabric traffic <em>falls</em> while the effective
                    all-reduce rate (how fast the training job gets its
                    numbers added up) rises, because the switches start
                    doing the adding. Click a block to see what it is; the
                    narrated walk-through lives under Guided tour.
                  </>
                ) : (
                  <>
                    Highlighted blocks are the parts doing work at this
                    step. Watch the manager (UFM / SM): lit only while it
                    maps and programs the fabric, dark forever after —
                    data never passes through it. Then watch the SHARP
                    step, where fabric traffic <em>falls</em> while the
                    effective all-reduce rate rises, because the switches
                    start doing the arithmetic. Click a block to pin what
                    it is; the narrated walk-through lives under Guided
                    tour.
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
