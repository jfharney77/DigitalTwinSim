export function Legend() {
  return (
    <div className="an-panel">
      <h2>Flows</h2>
      <div className="legend">
        <div>
          <i style={{ background: "var(--flow-ac)" }} />
          AC power (adapter → system)
        </div>
        <div>
          <i style={{ background: "var(--flow-charge)" }} />
          Charging (adapter → battery)
        </div>
        <div>
          <i style={{ background: "var(--flow-hybrid)" }} />
          Hybrid supplement (battery → system)
        </div>
        <div>
          <i style={{ background: "var(--flow-off)" }} />
          Idle path (no power moving)
        </div>
      </div>
    </div>
  );
}
