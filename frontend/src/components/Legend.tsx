export function Legend() {
  return (
    <div className="an-panel">
      <h2>Legend</h2>
      <div className="legend">
        <div>
          <i style={{ background: "var(--mem-active)" }} />
          Memory / HBM transfer
        </div>
        <div>
          <i style={{ background: "var(--core-on)" }} />
          Core computing (MAC)
        </div>
        <div>
          <i style={{ background: "var(--core-hot)" }} />
          Result written
        </div>
        <div>
          <i style={{ background: "var(--core-off)" }} />
          Core idle
        </div>
      </div>
    </div>
  );
}
