export function Legend() {
  // Every color the die can paint, incl. the stall state the legend used to
  // omit (spec_21 #5); titles explain on hover.
  const entries: [string, string, string][] = [
    [
      "var(--mem-active)",
      "Memory / HBM transfer",
      "The memory blocks light while operands stream to shared memory.",
    ],
    [
      "var(--stall)",
      "Stalled — waiting on HBM",
      "Cores that want data the memory system hasn't delivered yet; the UI dwells here because the wait dominates real workloads.",
    ],
    [
      "var(--core-on)",
      "Core computing (MAC)",
      "A lane doing multiply-accumulate work this step.",
    ],
    [
      "var(--core-hot)",
      "Result written",
      "The final accumulation flushed to the output matrix.",
    ],
    [
      "var(--core-off)",
      "Core idle",
      "No cell mapped to this lane this step — small matrices cannot fill a big die.",
    ],
  ];
  return (
    <div className="an-panel">
      <h2>Legend</h2>
      <div className="legend">
        {entries.map(([color, label, explain]) => (
          <div key={label} title={explain}>
            <i style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
