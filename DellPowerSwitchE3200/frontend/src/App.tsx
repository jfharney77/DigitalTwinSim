import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchBoot, fetchTour } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ChassisView } from "./components/ChassisView";
import { BootControls } from "./components/BootControls";
import { BootCounters } from "./components/BootCounters";
import { LevelControl } from "./components/LevelControl";
import { Timeline, TourPlayer, TwinLayout } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { useLevel } from "./level";
import type { BootState, ChassisAnatomy, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "boot" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "boot";
}

// The header tabs, as data — TwinLayout renders them.
const TABS = [
  { id: "boot", label: "Boot" },
  { id: "anatomy", label: "Inside the switch" },
  { id: "components", label: "Components & options" },
  { id: "usecases", label: "Use cases" },
  { id: "tour", label: "Guided tour" },
] as const satisfies readonly { id: Page; label: string }[];

const PAGE_HASH: Record<Page, string> = {
  boot: "",
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
  ports: "#12233a",
  uplink: "#122b2b",
  poe: "#2b1a1a",
  asic: "#2b2412",
  cpu: "#241f33",
  mgmt: "#12282e",
  cooling: "#16281a",
  power: "#1a2433",
};

const KIND_LABEL: Record<RegionKind, string> = {
  ports: "access ports",
  uplink: "uplinks (SFP+/SFP28/QSFP28)",
  poe: "PoE power subsystem",
  asic: "switching ASIC (data plane)",
  cpu: "control plane (CPU, network OS)",
  mgmt: "management & console",
  cooling: "variable-speed fans",
  power: "power supplies",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<regionId>).
    // The trace page owns every other hash (#step=, #phase=), so it only
    // rewrites the hash when it still names another page.
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) window.location.hash = want;
    document.body.classList.add("dell-body");
  }, [page]);

  // Follow hash changes made outside the tabs (the use-case page's "Go
  // deeper" buttons, the browser's back/forward) so the URL and page agree.
  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const [anatomy, setAnatomy] = useState<ChassisAnatomy | null>(null);
  const [trace, setTrace] = useState<BootState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply a #step=/#phase= deep link only on the first successful trace load,
  // so a reading-level refetch does not yank the cursor back.
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
    Promise.all([fetchAnatomy(), fetchBoot()])
      .then(([an, bt]) => {
        setAnatomy(an);
        setTrace(bt.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(bt.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (its narration is leveled prose).
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
      // Linger on the long stage (network-OS boot) so its real-world cost is
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
    <TwinLayout
      title={"PowerSwitch\u00a0E3200-ON"}
      tabs={TABS}
      active={page}
      onTab={setPage}
      subtitle={
        page === "boot" && state
          ? `${state.label} · t+${state.elapsedSeconds}s`
          : undefined
      }
      aside={<LevelControl />}
    >
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
              // ChassisView draws a 2.5-unit outline margin and a 4-unit
              // orientation-label strip: 105 x 57 for the 100 x 48 map.
              stageAspect={105 / 57}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
                // A region picked while exploring belongs to that pause, not
                // to the next beat's story.
                setRegionId(null);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the boot page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <ChassisView
                  anatomy={anatomy}
                  active={stage.lit}
                  // The explore highlight only while the viewer has taken
                  // over; once the tour resumes, only the beat's own regions
                  // stand out.
                  selected={stage.takenOver ? regionId : null}
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
                      Boot trace: <strong>{state.label}</strong> · t+
                      {state.elapsedSeconds}s · {state.powerWatts} W
                      (illustrative)
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

      {page === "boot" && (
        <>
          <div className="an-hero">
            <h2>From AC to forwarding traffic</h2>
            <p>
              A switch does not go straight from cold to moving packets. It
              boots like a small computer first: standby power, then the CPU,
              then the boot loader — where ONIE, the open-networking
              installer, runs on a factory-fresh unit and is bypassed once a
              network OS is installed — starts that network OS (SmartFabric
              OS10 or Enterprise SONiC), which programs
              the switching ASIC, brings the ports up, delivers PoE to the
              devices hanging off them, and only then forwards at line rate.
              Play the trace and watch each stage light up the hardware it runs
              on.
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
              <Timeline
                steps={trace.map((st) => ({
                  phase: st.phase,
                  cycleCost: st.cycleCost,
                  label: st.label,
                }))}
                cursor={cursor}
                onCursor={(step) => {
                  stop();
                  setCursor(step);
                }}
              />
              <div className="mini an-hint">
                Highlighted blocks are the parts doing work at this step. Click
                a block to pin what it is; the full tour lives under Inside the
                switch.
              </div>
            </div>
          </div>

          <aside className="controls">
            <BootControls
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
            <BootCounters
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
    </TwinLayout>
  );
}
