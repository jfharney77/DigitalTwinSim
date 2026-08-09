// Wire types for the display physics simulator. These mirror the pydantic
// models in backend/app/models.py (snake_case → camelCase).

export type PanelModel = "edge-27" | "miniled-32";
export type ContentProfile = "dark" | "mixed" | "bright" | "hdr";

export interface DisplayConfig {
  model: PanelModel;
  brightnessPct: number;
  content: ContentProfile;
  localDimming: boolean;
  hubLaptopW: number;
}

export interface Lifecycle {
  hoursPerDay: number;
  daysPerYear: number;
  serviceYears: number;
  gridKgco2PerKwh: number;
}

export type EventAction =
  | "set-brightness"
  | "set-content"
  | "set-dimming"
  | "hub-plug"
  | "hub-unplug"
  | "standby"
  | "wake";

export interface SimEvent {
  atS: number;
  action: EventAction;
  value?: number | null;
  content?: ContentProfile | null;
}

export interface Scenario {
  config: DisplayConfig;
  lifecycle: Lifecycle;
  durationS: number;
  events: SimEvent[];
}

export type RuleLevel = "ok" | "warning" | "error";

export interface Validation {
  ruleId: string;
  level: RuleLevel;
  message: string;
  source: string;
}

export interface SimState {
  t: number;
  on: boolean;
  brightnessPct: number;
  content: ContentProfile;
  electronicsW: number;
  backlightW: number;
  hubOutW: number;
  hubLossW: number;
  dcPowerW: number;
  acPowerW: number;
  heatW: number;
  litFraction: number;
  zonesLit: number;
  cumulativeWh: number;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface CarbonBreakdown {
  embodiedKg: number;
  useKg: number;
  lifetimeKg: number;
  embodiedPct: number;
  usePct: number;
  annualKwh: number;
  avgOnPowerW: number;
}

export interface Summary {
  peakAcW: number;
  steadyAcW: number;
  standbyW: number;
  carbon: CarbonBreakdown;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "panel"
  | "backlight"
  | "electronics"
  | "hub"
  | "power"
  | "chassis";

export interface PanelRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface PanelMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: PanelRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ModelPreset {
  id: string;
  name: string;
  blurb: string;
  config: DisplayConfig;
}

export interface GuidedScenario {
  id: string;
  title: string;
  narration: string[];
  question: string;
  scenario: Scenario;
}

export interface Explain {
  id: string;
  title: string;
  equation: string;
  inputs: string[];
  explanation: string;
}

export interface ConstantEntry {
  value: number;
  unit: string;
  source: string;
  estimated: boolean;
  blurb: string;
}

export interface ConstantsResponse {
  constants: Record<string, ConstantEntry>;
}
