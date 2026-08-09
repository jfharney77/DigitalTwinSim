import type {
  FactoryConfig,
  FactoryPreset,
  JobPreset,
  TrainingJob,
  Validation,
} from "../types";
import { GPU_WATT_TIERS } from "../types";

// The build panel: size the factory's six blocks, with the validation
// findings inline — the sizing review as a live document.

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field cfg-row">
      <span className="cfg-label">{label}</span>
      {children}
    </label>
  );
}

export function BuildPanel({
  config,
  job,
  presets,
  jobPresets,
  validations,
  onChange,
  onJobChange,
  onPreset,
}: {
  config: FactoryConfig;
  job: TrainingJob;
  presets: FactoryPreset[];
  jobPresets: JobPreset[];
  validations: Validation[];
  onChange: (c: FactoryConfig) => void;
  onJobChange: (j: TrainingJob) => void;
  onPreset: (p: FactoryPreset) => void;
}) {
  const set = (patch: Partial<FactoryConfig>) => onChange({ ...config, ...patch });
  const problems = validations.filter((v) => v.level !== "ok");
  const gpus = config.compute.racks * config.compute.gpusPerRack;
  const demand = gpus * job.dataGbpsPerGpu;

  return (
    <div className="an-panel">
      <h2>Size the factory</h2>
      <div className="btnrow cfg-presets">
        {presets.map((p) => (
          <button key={p.id} title={p.blurb} onClick={() => onPreset(p)}>
            {p.name}
          </button>
        ))}
      </div>

      <Row label={`Racks · ${config.compute.racks} (${gpus.toLocaleString()} GPUs)`}>
        <input
          type="range" min={1} max={64} value={config.compute.racks}
          onChange={(e) =>
            set({ compute: { ...config.compute, racks: +e.target.value } })
          }
        />
      </Row>
      <Row label="GPU class">
        <select
          value={config.compute.gpuPeakW}
          onChange={(e) =>
            set({ compute: { ...config.compute, gpuPeakW: +e.target.value } })
          }
        >
          {GPU_WATT_TIERS.map((w) => (
            <option key={w} value={w}>
              {w} W {w === 700 ? "(H100-class)" : w === 1000 ? "(B200-class)" : "(GB200-class)"}
            </option>
          ))}
        </select>
      </Row>
      <Row label="Fabric">
        <select
          value={config.fabric.type}
          onChange={(e) =>
            set({ fabric: { ...config.fabric, type: e.target.value as FactoryConfig["fabric"]["type"] } })
          }
        >
          <option value="quantum-ib">Quantum InfiniBand</option>
          <option value="spectrum-x">Spectrum-X Ethernet</option>
        </select>
      </Row>
      <Row label={`Oversubscription · ${config.fabric.oversubscription.toFixed(1)}:1`}>
        <input
          type="range" min={1} max={4} step={0.5}
          value={config.fabric.oversubscription}
          onChange={(e) =>
            set({ fabric: { ...config.fabric, oversubscription: +e.target.value } })
          }
        />
      </Row>
      <Row label={`Data platform · ${config.data.storageGbps.toLocaleString()} GB/s (demand ${demand.toFixed(0)})`}>
        <input
          type="range" min={50} max={12000} step={50}
          value={config.data.storageGbps}
          onChange={(e) => set({ data: { storageGbps: +e.target.value } })}
        />
      </Row>
      <Row label={`Facility budget · ${config.facility.mwBudget.toFixed(2)} MW`}>
        <input
          type="range" min={0.1} max={12} step={0.05}
          value={config.facility.mwBudget}
          onChange={(e) =>
            set({ facility: { ...config.facility, mwBudget: +e.target.value } })
          }
        />
      </Row>
      <Row label="Cooling">
        <select
          value={config.facility.cooling}
          onChange={(e) =>
            set({ facility: { ...config.facility, cooling: e.target.value as FactoryConfig["facility"]["cooling"] } })
          }
        >
          <option value="liquid">Direct liquid (PUE ≈ 1.15)</option>
          <option value="air">Air (PUE ≈ 1.45)</option>
        </select>
      </Row>
      <Row label={`Checkpoint interval · ${config.resilience.checkpointIntervalMin} min`}>
        <input
          type="range" min={5} max={720} step={5}
          value={config.resilience.checkpointIntervalMin}
          onChange={(e) =>
            set({
              resilience: {
                ...config.resilience,
                checkpointIntervalMin: +e.target.value,
              },
            })
          }
        />
      </Row>
      <Row label={`GPU MTBF · ${(config.resilience.gpuMtbfH / 1000).toFixed(0)}k h`}>
        <input
          type="range" min={10000} max={200000} step={5000}
          value={config.resilience.gpuMtbfH}
          onChange={(e) =>
            set({
              resilience: { ...config.resilience, gpuMtbfH: +e.target.value },
            })
          }
        />
      </Row>
      <Row label={`Energy · $${config.costs.usdPerKwh.toFixed(2)}/kWh`}>
        <input
          type="range" min={0.03} max={0.3} step={0.01}
          value={config.costs.usdPerKwh}
          onChange={(e) =>
            set({ costs: { ...config.costs, usdPerKwh: +e.target.value } })
          }
        />
      </Row>

      <h2 style={{ marginTop: 10 }}>Training job</h2>
      <div className="btnrow cfg-presets">
        {jobPresets.map((p) => (
          <button key={p.id} onClick={() => onJobChange(p.job)}>
            {p.name}
          </button>
        ))}
      </div>
      <Row label={`Data appetite · ${job.dataGbpsPerGpu.toFixed(1)} GB/s per GPU`}>
        <input
          type="range" min={0.5} max={8} step={0.5}
          value={job.dataGbpsPerGpu}
          onChange={(e) => onJobChange({ ...job, dataGbpsPerGpu: +e.target.value })}
        />
      </Row>

      <div className="rules">
        {problems.length === 0 && (
          <div className="mini rule-ok">✓ The design passes its own sizing review.</div>
        )}
        {problems.map((v) => (
          <div key={v.ruleId} className={`mini rule-${v.level}`} title={v.source}>
            {v.level === "error" ? "■" : "▲"} {v.message}
          </div>
        ))}
      </div>
    </div>
  );
}
