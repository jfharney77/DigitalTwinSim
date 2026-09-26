import { useLevel } from "../level";
import type { Explain, SimState, Summary } from "../types";

// The six headline instruments — the whole point of the capstone: one
// dashboard where every earlier lesson is a line item. Explain mode adds
// the governing equation under a tile, with live values substituted.

function fmtTokens(v: number): string {
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)} M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)} k`;
  return v.toFixed(0);
}

// Dollars at $k resolution below a million, so the early hours can be
// told apart (the engine carries $M to three decimals).
function fmtUsd(m: number): string {
  return m < 1 ? `$${(m * 1000).toFixed(0)} k` : `$${m.toFixed(2)} M`;
}

function substituted(id: string, s: SimState, summary?: Summary | null): string {
  switch (id) {
    case "tokens-per-s":
      return `${fmtTokens(s.tokensPerS)} tok/s = ${s.gpusOnline} × rate × ${(s.gpuUtilPct / 100).toFixed(2)}`;
    case "idle-data":
      if (s.storageDemandGbps <= 0)
        return `no demand yet: the GPUs ask for data only once training starts (${s.storageSupplyGbps.toFixed(0)} GB/s available)`;
      return `${s.gpuIdleDataPct.toFixed(0)}% = (1 − min(1, ${s.storageSupplyGbps.toFixed(0)} ÷ ${s.storageDemandGbps.toFixed(0)} GB/s)) × 100`;
    case "facility-mw":
      return `${s.facilityMw.toFixed(2)} MW = ${s.itMw.toFixed(2)} IT × PUE ${s.pue.toFixed(2)} (budget ${s.mwBudget.toFixed(2)})`;
    case "pue":
      return s.itMw > 0
        ? `${s.pue.toFixed(2)} = ${s.facilityMw.toFixed(2)} MW facility ÷ ${s.itMw.toFixed(2)} MW IT`
        : `${s.pue.toFixed(2)} (nothing is drawing power yet)`;
    case "usd-per-mtok":
      if (s.tokensTotalB <= 0) return `${fmtUsd(s.costUsdM)} charged so far, no tokens yet`;
      return `$${s.usdPerMtok.toFixed(2)}/Mtok = ${fmtUsd(s.costUsdM)} ÷ ${s.tokensTotalB.toFixed(1)} B tokens`;
    case "ttft": {
      const t = summary?.timeToFirstTokenH ?? -1;
      if (t < 0) return "no training token in this run yet";
      if (t < 96) return `${t} h in total · now at hour ${s.tH}`;
      return `${t} h = 72 h procure + ${t - 96} h install + 24 h bring-up · now at hour ${s.tH}`;
    }
    default:
      return "";
  }
}

function Tile({
  label,
  value,
  sub,
  tone,
  explain,
  live,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "hero" | "warn" | "";
  explain?: Explain | null;
  live?: string;
}) {
  return (
    <div className={`headline-tile ${tone ?? ""}`}>
      <div className="mini headline-label">{label}</div>
      <div className="headline-value">{value}</div>
      {sub && <div className="mini headline-sub">{sub}</div>}
      {explain && (
        <div className="mini explain-card">
          <div className="explain-eq">{explain.equation}</div>
          {live && <div className="explain-live">{live}</div>}
          <div>{explain.explanation}</div>
          <div className="explain-chain">{explain.inputs.join(" → ")}</div>
        </div>
      )}
    </div>
  );
}

export function Headline({
  state,
  summary,
  explains,
  explainOn,
}: {
  state: SimState | null;
  summary: Summary | null;
  explains: Explain[];
  explainOn: boolean;
}) {
  const s = state;
  const level = useLevel();
  const ex = (id: string) =>
    explainOn && s ? explains.find((e) => e.id === id) ?? null : null;
  const ttft = summary?.timeToFirstTokenH ?? -1;
  const ttftText =
    ttft < 0 ? "—" : s && s.tH < ttft ? `T−${ttft - s.tH} h` : `${ttft} h`;

  return (
    <div className="headline-grid">
      <Tile
        label="tokens / second"
        value={s ? fmtTokens(s.tokensPerS) : "—"}
        sub={s ? `${s.tokensTotalB.toFixed(1)} B so far, at this hour · ${s.gpusOnline.toLocaleString()} GPUs` : undefined}
        explain={ex("tokens-per-s")}
        live={s ? substituted("tokens-per-s", s) : undefined}
      />
      <Tile
        label="GPU idle — waiting for data"
        value={s ? `${s.gpuIdleDataPct.toFixed(0)}%` : "—"}
        sub={
          !s
            ? undefined
            : s.storageDemandGbps > 0
              ? `${Math.min(s.storageSupplyGbps, s.storageDemandGbps).toFixed(0)} of ${s.storageDemandGbps.toFixed(0)} GB/s served`
              : `no data demand until training · ${s.storageSupplyGbps.toFixed(0)} GB/s available`
        }
        tone={s && s.gpuIdleDataPct > 10 ? "warn" : "hero"}
        explain={ex("idle-data")}
        live={s ? substituted("idle-data", s) : undefined}
      />
      <Tile
        label="facility power"
        value={s ? `${s.facilityMw.toFixed(2)} MW` : "—"}
        sub={s ? `budget ${s.mwBudget.toFixed(2)} MW${s.powerCapped ? " · CAPPED" : ""}` : undefined}
        tone={s?.powerCapped ? "warn" : ""}
        explain={ex("facility-mw")}
        live={s ? substituted("facility-mw", s) : undefined}
      />
      <Tile
        label="PUE"
        value={s ? s.pue.toFixed(2) : "—"}
        sub={s ? `building ÷ IT power · ${s.itMw.toFixed(2)} MW IT` : undefined}
        explain={ex("pue")}
        live={s ? substituted("pue", s) : undefined}
      />
      <Tile
        label="$ / million tokens"
        value={s && s.usdPerMtok > 0 ? `$${s.usdPerMtok.toFixed(2)}` : "—"}
        sub={
          s
            ? `${fmtUsd(s.costUsdM)} charged so far · ${
                level <= 2
                  ? "hardware spread over its life + energy"
                  : "amortized hardware + energy"
              } · illustrative`
            : undefined
        }
        explain={ex("usd-per-mtok")}
        live={s ? substituted("usd-per-mtok", s) : undefined}
      />
      <Tile
        label="time to first training token"
        value={ttftText}
        sub={s ? `phase: ${s.phase}` : undefined}
        explain={ex("ttft")}
        live={s ? substituted("ttft", s, summary) : undefined}
      />
    </div>
  );
}
