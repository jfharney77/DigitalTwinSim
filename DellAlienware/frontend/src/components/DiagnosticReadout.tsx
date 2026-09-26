import type { ChargeLimiter, ChargeMode, PowerState, TraceScenario } from "../types";

// What the owner can read off the machine at this step of the charging
// diagnostics walk: the BIOS adapter line, the battery status line, the charge mode and the pack
// temperature, then the diagnosis those readings support. Everything here is
// the backend's state; this component only lays it out.

export const LIMITER_LABEL: Record<ChargeLimiter, string> = {
  none: "nothing: full charge rate",
  "charge-cap": "BIOS charge mode limit",
  taper: "constant-voltage taper (normal)",
  budget: "adapter budget spent on the system",
  temperature: "battery over its charge temperature",
  adapter: "adapter not recognized",
  full: "battery full",
};

const MODE_LABEL: Record<ChargeMode, string> = {
  "primarily-ac": "Primarily AC Use",
  standard: "Standard",
};

export function DiagnosticReadout({
  state,
  info,
}: {
  state: PowerState;
  info: TraceScenario | null;
}) {
  const limiter = state.chargeLimiter ?? "none";
  const fault = (state.failedRegions ?? []).length > 0;
  const check =
    info?.checks.find(
      (c) => c.phase === state.phase && c.limiter === limiter,
    ) ?? null;
  return (
    <div className="diag">
      <div className="diag-screen" aria-label="BIOS and battery status readouts">
        <div className="stat">
          <span>AC Adapter</span>
          <span className={state.adapterReadout === "Unknown" ? "diag-bad" : ""}>
            {state.adapterReadout ?? "—"}
          </span>
        </div>
        <div className="stat">
          <span>Battery status</span>
          <span className={fault ? "diag-bad" : ""}>{state.batteryReadout ?? "—"}</span>
        </div>
        <div className="stat">
          <span>Charge mode</span>
          <span>
            {MODE_LABEL[state.chargeMode ?? "standard"]} · stops at{" "}
            {Math.round(state.chargeCapPct ?? 100)}%
          </span>
        </div>
        <div className="stat">
          <span>Battery temperature</span>
          <span className={limiter === "temperature" ? "diag-bad" : ""}>
            {state.packTempC !== undefined ? `${state.packTempC} °C` : "—"}
          </span>
        </div>
      </div>
      {check && (
        <div className="diag-check">
          <p>
            <strong>What the owner sees.</strong> {check.symptom}
          </p>
          <p>
            <strong>What it is.</strong> {check.cause}
          </p>
          <p>
            <strong>What to do.</strong> {check.action}
          </p>
        </div>
      )}
      {info && (
        <p className="mini">
          {info.illustrative}{" "}
          {info.sources.map((src, i) => (
            <span key={src.url}>
              {i > 0 && " · "}
              <a href={src.url} target="_blank" rel="noreferrer">
                {src.label.split(" — ")[0]}
              </a>
            </span>
          ))}
        </p>
      )}
    </div>
  );
}
