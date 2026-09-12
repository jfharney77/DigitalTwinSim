import type { ReactNode } from "react";

export type Metric = {
  label: string;
  value: ReactNode;
  /** Marks a number the twin exists to show — rendered with the accent. */
  hero?: boolean;
};

/**
 * The counters panel: a stack of label/value rows.
 *
 * Every twin has one, every twin called it something different
 * (`PowerOnCounters`, `FabricCounters`, `DetectCounters`, `Instruments`), and
 * every one of them wrote out the same `.stat` markup by hand.
 *
 * `hero` is for the field the twin exists to show — `droppedPackets`,
 * `downtimeSeconds`, `implicitTrustGrants`, `operatorActions`. Those numbers
 * are the argument; the rest is context.
 */
export function MetricReadout({
  title = "Telemetry",
  metrics,
  note,
}: {
  title?: string;
  metrics: readonly Metric[];
  note?: ReactNode;
}) {
  return (
    <div className="an-panel">
      <h2>{title}</h2>
      {metrics.map((metric) => (
        <div key={metric.label} className={metric.hero ? "stat tw-hero" : "stat"}>
          <span>{metric.label}</span>
          <span>{metric.value}</span>
        </div>
      ))}
      {note && (
        <div className="mini" style={{ marginTop: 8 }}>
          {note}
        </div>
      )}
    </div>
  );
}
