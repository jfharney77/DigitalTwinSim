import { useEffect, useState } from "react";
import { simulate } from "../api";
import type { FleetConfig, GuidedScenario } from "../types";

// A guided scenario's builds, run side by side: the scenario's own
// workload, events and duration under each variant's config. The table is
// the evidence the scenario's question asks about; a row loads its build.

interface Row {
  label: string;
  config: FleetConfig;
  hoursPerMonth: number;
  hoursTotal: number;
  exposureDays: number;
  deploys: number;
  deployHours: number;
}

export function ScenarioVariants({
  guided,
  current,
  onLoad,
}: {
  guided: GuidedScenario;
  current: FleetConfig;
  onLoad: (config: FleetConfig) => void;
}) {
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    let live = true;
    setRows([]);
    Promise.all(
      guided.variants.map((v) =>
        simulate({ ...guided.scenario, config: v.config }).then((r) => ({
          label: v.label,
          config: v.config,
          hoursPerMonth: r.trace[r.trace.length - 1]?.adminHoursPerMonth ?? 0,
          hoursTotal: r.summary.adminHoursTotal,
          exposureDays: r.summary.exposureDays,
          deploys: r.summary.workloadsDeployed,
          deployHours: r.summary.deployHours,
        })),
      ),
    )
      .then((rs) => {
        if (live) setRows(rs);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
    // The variants are scenario data: rerun only when the scenario changes.
  }, [guided.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (guided.variants.length === 0) return null;
  const showExposure = rows.some((r) => r.exposureDays > 0);
  const showDeploys = rows.some((r) => r.deploys > 0);
  const same = (a: FleetConfig, b: FleetConfig) =>
    JSON.stringify(a) === JSON.stringify(b);
  const days = guided.scenario.durationD;

  return (
    <div className="scenario-variants">
      <table>
        <thead>
          <tr>
            <th>Build, over the same {days} days</th>
            <th>admin-hours / month at the end</th>
            <th>admin-hours total</th>
            {showDeploys && <th>deploys · hours</th>}
            {showExposure && <th>exposure days</th>}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={5}>Running the builds…</td></tr>
          )}
          {rows.map((r) => (
            <tr key={r.label} className={same(r.config, current) ? "active" : ""}>
              <td>
                <button onClick={() => onLoad(r.config)}>{r.label}</button>
              </td>
              <td>{r.hoursPerMonth.toFixed(1)}</td>
              <td>{r.hoursTotal.toFixed(1)}</td>
              {showDeploys && <td>{r.deploys} · {r.deployHours.toFixed(1)} h</td>}
              {showExposure && <td>{r.exposureDays}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
