// Mirrors the API's response models (backend/app/main.py, questions.py, intake.py, rules.py).

export type Mode = "today" | "health_first";
export type MemberId = "a" | "b" | "c";

export type ScreenKind =
  | "single_choice"
  | "multi_choice"
  | "date"
  | "height"
  | "weight"
  | "text"
  | "interstitial"
  | "condition_picker"
  | "health_benefit"
  | "health_permission"
  | "health_review";

export interface Option {
  id: string;
  label: string;
  free_text: boolean;
  exclusive: boolean;
}

export interface Screen {
  id: string;
  section: string;
  kind: ScreenKind;
  title: string;
  subtitle: string | null;
  options: Option[];
  optional: boolean;
  skip_label: string | null;
  units: string[];
  health: { kind: "fact" | "estimate"; rule: string } | null;
  modes: Mode[];
  catalog: string | null;
  review_rows: string[];
  read_types: string[];
}

export interface Section {
  id: string;
  title: string;
  assumed: boolean;
}

export interface Form {
  version: number;
  mode: Mode;
  sections: Section[];
  screens: Screen[];
}

export interface MemberSummary {
  id: MemberId;
  label: string;
  description: string;
}

export interface Condition {
  id: string;
  label: string;
  group: string;
}

export type AnswerValue = unknown;

export interface Answer {
  value: AnswerValue;
  source: "health_confirmed" | "health_changed" | "member";
}

export interface RuleResult {
  screen_id: string;
  rule: string;
  version: string;
  kind: "fact" | "estimate";
  status: "suggested" | "needs_check" | "ask";
  value: AnswerValue;
  evidence: string;
  source: string | null;
  observed_at: string | null;
}

export interface Measurement {
  value: number;
  unit: string;
  at: string;
  source: string;
}

/** HealthSummaryV1: the member's own Health data. Shown to them; never sent to the model. */
export interface HealthSummary {
  schema_version: number;
  generated_at: string;
  read_types_with_data: string[];
  biological_sex: string | null;
  date_of_birth: string | null;
  latest_height: Measurement | null;
  latest_weight: Measurement | null;
  workouts_last_28d: number;
  workouts_recorded: number;
  daily_steps_30d: { day: string; count: number }[];
}

export interface EgressEntry {
  id: number;
  purpose: string;
  status: string;
  model: string;
  request: { system?: string; messages?: { role: string; content: string }[] } | null;
  result: Record<string, unknown> | null;
  error: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface SessionState {
  id: string;
  member_id: MemberId;
  mode: Mode;
  next_screen_id: string | null;
  answers: Record<string, Answer>;
  suggestions: Record<string, RuleResult>;
  review_rows: string[];
  health_summary: HealthSummary | null;
  tap_count: number;
  finished: boolean;
}
