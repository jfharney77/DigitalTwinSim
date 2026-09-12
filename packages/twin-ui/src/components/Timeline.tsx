import { useMemo } from "react";

export type TimelineStep = {
  /** The phase this step belongs to. Adjacent same-phase steps form a band. */
  phase: string;
  /** How long the twin dwells here. Wider bands are slower stages. */
  cycleCost?: number;
  label?: string;
};

/**
 * The trace as a scrubbable strip of phase bands.
 *
 * A band's width is its share of the trace's total cycle cost, so the strip
 * shows at a glance what every twin's tests assert somewhere: which stage is
 * the long one. Clicking anywhere moves the cursor — the consumer still owns
 * it, as it owns the clock.
 */
export function Timeline({
  steps,
  cursor,
  onCursor,
  ariaLabel = "Trace timeline",
}: {
  steps: readonly TimelineStep[];
  cursor: number;
  onCursor?: (step: number) => void;
  ariaLabel?: string;
}) {
  const bands = useMemo(() => {
    const total = steps.reduce((sum, step) => sum + Math.max(1, step.cycleCost ?? 1), 0) || 1;
    const out: { phase: string; from: number; to: number; width: number }[] = [];
    let offset = 0;
    steps.forEach((step, index) => {
      const cost = Math.max(1, step.cycleCost ?? 1);
      const last = out[out.length - 1];
      if (last && last.phase === step.phase) {
        last.to = index;
        last.width += (cost / total) * 100;
      } else {
        out.push({ phase: step.phase, from: index, to: index, width: (cost / total) * 100 });
      }
      offset += cost;
    });
    void offset;
    return out;
  }, [steps]);

  if (steps.length === 0) return null;

  return (
    <div className="tw-timeline" role="group" aria-label={ariaLabel}>
      <div className="tw-timeline-track">
        {bands.map((band) => {
          const holdsCursor = cursor >= band.from && cursor <= band.to;
          return (
            <button
              key={`${band.phase}-${band.from}`}
              type="button"
              className={holdsCursor ? "tw-band active" : "tw-band"}
              style={{ width: `${band.width}%` }}
              title={`${band.phase} — steps ${band.from + 1}–${band.to + 1}`}
              onClick={() => onCursor?.(band.from)}
            >
              <span>{band.phase}</span>
            </button>
          );
        })}
      </div>
      <input
        className="tw-timeline-scrub"
        type="range"
        min={0}
        max={steps.length - 1}
        value={cursor}
        aria-label="Step"
        onChange={(event) => onCursor?.(Number(event.target.value))}
      />
      <div className="tw-timeline-caption">
        <span>{steps[cursor]?.label ?? steps[cursor]?.phase}</span>
        <span>
          step {cursor + 1} / {steps.length}
        </span>
      </div>
    </div>
  );
}
