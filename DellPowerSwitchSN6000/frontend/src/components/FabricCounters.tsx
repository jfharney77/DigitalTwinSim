import type { FabricPhase, FabricState, LinkStatus } from "../types";
import { useLevel } from "../level";

const PHASE_LABEL: Record<FabricPhase, string> = {
  off: "off — cabled, dark",
  power: "switches booting",
  linktrain: "links training",
  topology: "routing converging",
  ready: "fabric ready",
  collective: "all-reduce running",
  congestion: "congestion — buffers filling",
  reroute: "adaptive routing",
  steady: "steady state",
  degrade: "optic degrading — FEC coping",
  blind: "link up, job slow",
  telemetry: "error counters name the port",
  steer: "routing withdrawn, link still up",
  drain: "port shut down on purpose",
  replace: "optic replaced, retraining",
  restored: "eight clean uplinks",
};

const STATUS_LABEL: Record<LinkStatus, string> = {
  up: "up",
  "admin-down": "shut down by operator",
  training: "retraining",
};

// Seconds are readable while a trace lasts minutes; the gray-link failure
// runs for hours, and "t+25500s" is not a number anybody reads. Anything an
// hour or longer is shown as hours and minutes.
export function elapsedLabel(seconds: number): string {
  if (seconds < 3600) return `t+${seconds}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds - h * 3600) / 60);
  return m === 0 ? `t+${h}h` : `t+${h}h ${m}m`;
}

// Two telemetry rows are named in the step prose, so their labels have to
// survive the reading level the prose is being read at. At levels 1–2 the
// captions say what the mechanism does in words and put the letters in
// brackets; the rows do the same, so a reader sent to look for "the rows
// for marked packets and pauses" finds rows by those names.
export function ecnRowLabel(level: number): string {
  return level <= 2
    ? "marked so senders slow down (ECN), busiest link"
    : "ECN-marked, busiest link";
}

export function pfcRowLabel(level: number): string {
  return level <= 2 ? "pauses, one traffic class (PFC)" : "PFC pauses";
}

// "leaf-l2:spine-s1" -> "leaf 2 to spine 1"
function linkName(id: string): string {
  return id
    .split(":")
    .map((end) => end.replace(/^(\w+)-\w(\d+)$/, "$1 $2"))
    .join(" to ");
}

export function FabricCounters({
  state,
  stepIndex,
  stepCount,
  failing = false,
  baselineMs = 0,
  note = "",
}: {
  // The scenario's leveled note under the rows (backend/app/scenarios.py).
  note?: string;
  // True on a failure scenario: the panel leads with that scenario's hero
  // number (all-reduce time) and adds the per-link rows.
  failing?: boolean;
  // All-reduce time on the scenario's first, healthy step.
  baselineMs?: number;
  state: FabricState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const level = useLevel();
  const hot = state !== null && state.peakLinkPercent >= 90;
  const slow =
    state !== null && baselineMs > 0 && state.collectiveMs >= 1.5 * baselineMs;
  const located = state?.sickLinkLocated ?? false;
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      {failing && (
        <div className="stat">
          <span>all-reduce time</span>
          <span className={slow ? "stat-bad" : undefined}>
            {state ? `${state.collectiveMs} ms` : "—"}
            {slow ? ` — ${(state!.collectiveMs / baselineMs).toFixed(1)}× slower` : ""}
          </span>
        </div>
      )}
      <div className="stat">
        <span>fabric throughput</span>
        <span>{state ? `${state.fabricTbps} Tb/s` : "0 Tb/s"}</span>
      </div>
      <div className="stat">
        <span>busiest link</span>
        <span>
          {state ? `${state.peakLinkPercent}%${hot ? " — saturated" : ""}` : "0%"}
        </span>
      </div>
      <div className="stat">
        <span>dropped packets</span>
        <span>{state ? state.droppedPackets : 0}</span>
      </div>
      <div className="stat">
        <span>{ecnRowLabel(level)}</span>
        <span>{state ? `${state.ecnMarkedPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>{pfcRowLabel(level)}</span>
        <span>{state ? `${state.pfcPausesPerSec} /s` : "0 /s"}</span>
      </div>
      {failing && state && (
        <>
          <div className="stat">
            <span>uplinks reporting up</span>
            <span>{state.sickLinkStatus === "up" ? "8 / 8" : "7 / 8"}</span>
          </div>
          <div className="stat">
            <span>NIC retransmits</span>
            <span className={state.retransmitsPerSec > 0 ? "stat-bad" : undefined}>
              {state.retransmitsPerSec.toLocaleString()} /s
            </span>
          </div>
          <div className="stat">
            <span>per-link symbol errors</span>
            <span className={located && state.symbolErrorsPerSec > 0 ? "stat-bad" : undefined}>
              {located
                ? `${state.symbolErrorsPerSec.toLocaleString()} /s`
                : "not on any dashboard"}
            </span>
          </div>
          <div className="stat">
            <span>suspect link</span>
            <span className={located && state.sickLinkStatus !== "up" ? "stat-bad" : undefined}>
              {located && state.sickLink
                ? `${linkName(state.sickLink)} — ${STATUS_LABEL[state.sickLinkStatus ?? "up"]}${
                    state.trafficSteered ? ", no job traffic" : ""
                  }`
                : "none identified"}
            </span>
          </div>
        </>
      )}
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? elapsedLabel(state.elapsedSeconds) : "t+0s"}</span>
      </div>
      {note && (
        <div className="mini" style={{ marginTop: 8 }}>
          {note}
        </div>
      )}
    </div>
  );
}
