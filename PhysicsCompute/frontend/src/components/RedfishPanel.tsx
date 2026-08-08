import { useEffect, useState } from "react";
import { fetchRedfish } from "../api";
import type { SimState } from "../types";

// The iDRAC tab (spec 01 §5): the current SimState reshaped as the
// Redfish Thermal payload a real iDRAC would serve. The panel is the
// suite's "from sim to twin" argument: keep the query, swap the
// answerer.

export function RedfishPanel({
  state,
  product,
}: {
  state: SimState | null;
  product: string;
}) {
  const [payload, setPayload] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (!state || paused) return;
    fetchRedfish(state, product)
      .then((p) => {
        setPayload(p);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, [state, product, paused]);

  return (
    <div className="an-panel">
      <h2>iDRAC · mock Redfish explorer</h2>
      <div className="mini">
        <code>GET /redfish/v1/Chassis/System.Embedded.1/Thermal</code> —
        answered from the simulator's live state. A real digital twin
        keeps this exact query and points it at hardware; the DellIDRAC
        twin (:5177) walks the controller that would answer it.
      </div>
      <div className="btnrow" style={{ margin: "6px 0" }}>
        <button onClick={() => setPaused(!paused)}>
          {paused ? "Resume polling" : "Freeze response"}
        </button>
      </div>
      {error && <div className="mini an-error">{error}</div>}
      <pre className="redfish-json">
        {payload ? JSON.stringify(payload, null, 2) : "— run the sim —"}
      </pre>
    </div>
  );
}
