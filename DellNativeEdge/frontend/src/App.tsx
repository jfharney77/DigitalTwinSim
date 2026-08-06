import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchOnboard } from "./api";
import { ArchitecturePage } from "./components/ArchitecturePage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { PlatformView } from "./components/PlatformView";
import { OnboardControls } from "./components/OnboardControls";
import { OnboardCounters } from "./components/OnboardCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type { PlatformMap, OnboardState, RegionKind } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "onboard" | "architecture" | "capabilities" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#architecture")) return "architecture";
  if (h.startsWith("#capabilities")) return "capabilities";
  if (h.startsWith("#usecases")) return "usecases";
  return "onboard";
}

const PAGE_HASH: Record<Page, string> = {
  onboard: "",
  architecture: "architecture",
  capabilities: "capabilities",
  usecases: "usecases",
};

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

// Keep in sync with KIND_STYLE in PlatformView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  endpoint: "#2b2412",
  network: "#12233a",
  identity: "#0f2a30",
  orchestrator: "#1c1f3f",
  blueprint: "#241f33",
  catalog: "#22290f",
  policy: "#2b1a1a",
  observability: "#16281a",
};

const KIND_LABEL: Record<RegionKind, string> = {
  endpoint: "edge endpoints",
  network: "WAN",
  identity: "secure onboarding",
  orchestrator: "Orchestrator",
  blueprint: "blueprints",
  catalog: "app catalog",
  policy: "Zero Trust policy",
  observability: "observability",
};

export function App() {
  // Deep-linkable pages: /#architecture, /#capabilities, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    if (!window.location.hash.startsWith(`#${PAGE_HASH[page]}`)) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<PlatformMap | null>(null);
  const [trace, setTrace] = useState<OnboardState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

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
    Promise.all([fetchAnatomy(), fetchOnboard()])
      .then(([an, po]) => {
        setAnatomy(an);
        setTrace(po.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(po.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  const state = trace[cursor] ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on the attestation stage so its real-world cost shows.
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
        <h1>Dell NativeEdge</h1>
        <nav className="nav">
          <button
            className={page === "onboard" ? "active" : ""}
            onClick={() => setPage("onboard")}
          >
            Zero-touch onboarding
          </button>
          <button
            className={page === "architecture" ? "active" : ""}
            onClick={() => setPage("architecture")}
          >
            Architecture
          </button>
          <button
            className={page === "capabilities" ? "active" : ""}
            onClick={() => setPage("capabilities")}
          >
            Capabilities
          </button>
          <button
            className={page === "usecases" ? "active" : ""}
            onClick={() => setPage("usecases")}
          >
            Use cases
          </button>
        </nav>
        {page === "onboard" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedSeconds}s` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "architecture" && <ArchitecturePage />}
      {page === "capabilities" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "onboard" && (
        <>
          <div className="an-hero">
            <h2>Nobody touches the device</h2>
            <p>
              Every hardware twin in this repo assumes a person at the moment
              of truth — someone presses the power button, racks the machine,
              plugs in the adapter. An edge estate breaks that assumption:
              four hundred sites, no IT staff at any of them. So NativeEdge
              inverts the direction of trust. The device wakes, proves
              cryptographically that it is the machine Dell built, and asks
              the Orchestrator what it should become — OS, blueprint,
              workloads, policy, all pulled, never pushed. The only human
              action in the entire sequence is power and a network cable.
              Play the trace and watch the operator-actions counter reach
              one, and stop.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <PlatformView
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
                Watch the dwell on attestation — proving the device is the
                machine Dell built is the slow part, on purpose — and watch
                endpoints-online snap from zero to four when the
                Orchestrator claims the site as a set. Click a block to pin
                what it is; the full tour lives under Architecture.
              </div>
            </div>
          </div>

          <aside className="controls">
            <OnboardControls
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
            <OnboardCounters
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
