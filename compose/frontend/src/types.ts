// The wire shapes, mirroring compose/models.py and compose/catalog.py.
// camelCase on the wire (the shared alias generator).

export type SeamResult = {
  coupling: string;
  identity: string;
  lhs: number;
  rhs: number;
  unit: string;
  absError: number;
  tolerance: number;
  holds: boolean;
  worstTick: number | null;
  note: string;
  lhsKey: string | null;
  rhsKey: string | null;
};

export type Stage = {
  id: string;
  component: string;
  label: string;
  timeUnit: "s" | "h" | "d";
  scenario: Record<string, unknown>;
  injectedEvents: Record<string, unknown>[];
  injectedConfig: Record<string, unknown>;
  trace: Record<string, unknown>[];
  summary: Record<string, unknown>;
  validations: { level?: string; message?: string; rule?: string; source?: string }[];
  log: { atS?: number; atH?: number; atD?: number; message?: string; level?: string }[];
};

export type JoinedTick = { t: number; values: Record<string, number | null> };

export type ChartSeries = { key: string; label: string; role: "source" | "target" | "context" };
export type Chart = { title: string; unit: string; seam: boolean; series: ChartSeries[] };

export type Divergence = {
  instrument: string;
  aggregate: number;
  fed: number;
  tolerance: number;
  cause: string | null;
  explanation: string;
};

export type IterationRecord = {
  index: number;
  loopValue: number;
  residual: number;
  note: string;
  series: Record<string, number[]>;
};

export type CoupledTrace = {
  chainId: string;
  title: string;
  timeUnit: "s" | "h" | "d";
  stages: Stage[];
  seams: SeamResult[];
  iterations: number;
  converged: boolean;
  residualHistory: number[];
  iterationLog: IterationRecord[];
  timeline: JoinedTick[];
  charts: Chart[];
  divergences: Divergence[];
  notes: string[];
  illustrative: boolean;
  estimatedConstants: string[];
};

export type CouplingInfo = {
  id: string;
  title: string;
  source: string;
  target: string;
  sourceFields: string[];
  targetInputs: string[];
  units: string;
  timeBase: string;
  identity: string;
  tolerance: string;
  test: string;
  closedWith: string | null;
  blurb: string;
};

export type EngineRef = { component: string; label: string; frontendPort: number };

export type ChainInfo = {
  id: string;
  title: string;
  couplings: string[];
  closed: boolean;
  engines: EngineRef[];
  blurb: string;
  watch: string;
  defaultChain: Record<string, unknown>;
};

export type Constant = {
  value: number;
  unit: string;
  source: string;
  estimated: boolean;
  blurb: string;
};

export type ConstantsResponse = { constants: Record<string, Constant> };
