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
  | "health_review"
  | "voice";

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
  /** A voice screen: the questions one spoken answer fills in. */
  covers: string[];
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
  /** The same questions asked one per screen: screens, and the fewest taps they could take. */
  baseline: { screens: number; min_taps: number };
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
  source: "health_confirmed" | "health_changed" | "voice_confirmed" | "member";
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

export interface MatchResult {
  call_id: number;
  status: string;
  matches: { id: string; label: string; confidence: string }[];
  show_full_list: boolean;
}

export interface RunStats {
  screens_seen: number;
  filled_from_health: number;
  changed_from_health: number;
  estimates_taken: number;
  filled_from_voice: number;
}

/** A voice screen's questions filled from what the member said. `null` means not mentioned. */
export interface ExtractResult {
  call_id: number;
  status: string;
  answers: Record<string, AnswerValue>;
}

export interface SummaryResult {
  call_id: number;
  status: string;
  text: string;
  written_by_model: boolean;
  writer: string | null;
  health_values_filled: string[];
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
  stats: RunStats;
  finished: boolean;
  /** Simulated dictation for the voice screens: synthetic text the demo plays as if spoken. */
  voice_scripts: Record<string, string>;
}
