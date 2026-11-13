import type { AnswerValue, Condition, Screen } from "./types";
import { cmToFeetInches, kgToLb } from "./units";

const DATE = new Intl.DateTimeFormat("en-US", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

export function formatDate(iso: string): string {
  return DATE.format(new Date(`${iso.slice(0, 10)}T00:00:00Z`));
}

export function daysAgo(iso: string, now = Date.now()): string {
  const days = Math.floor((now - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

export function formatHeight(cm: number): string {
  const { feet, inches } = cmToFeetInches(cm);
  return `${feet} ft ${inches} in · ${cm} cm`;
}

export function formatWeight(kg: number): string {
  return `${kgToLb(kg)} lb · ${kg} kg`;
}

function optionLabel(screen: Screen, item: unknown): string {
  if (item && typeof item === "object" && "option" in item && "text" in item) return String(item.text);
  return screen.options.find((o) => o.id === item)?.label ?? String(item);
}

/** How an answer reads back to the member, for the review card and the dietitian view. */
export function formatAnswer(screen: Screen, value: AnswerValue, conditions: Condition[] = []): string {
  if (value === null || value === undefined) return screen.skip_label ?? "Skipped";
  switch (screen.kind) {
    case "single_choice":
      return optionLabel(screen, value);
    case "multi_choice":
      return Array.isArray(value) ? value.map((v) => optionLabel(screen, v)).join(", ") : String(value);
    case "date":
      return typeof value === "string" ? formatDate(value) : String(value);
    case "height":
      return value && typeof value === "object" && "cm" in value ? formatHeight(Number(value.cm)) : String(value);
    case "weight":
      return value && typeof value === "object" && "kg" in value ? formatWeight(Number(value.kg)) : String(value);
    case "condition_picker":
      if (value && typeof value === "object" && "condition_id" in value) {
        return conditions.find((c) => c.id === value.condition_id)?.label ?? String(value.condition_id);
      }
      return optionLabel(screen, value);
    default:
      return typeof value === "string" ? value : JSON.stringify(value);
  }
}

export const SHORT_LABELS: Record<string, string> = {
  sex_at_birth: "Sex at birth",
  date_of_birth: "Date of birth",
  height: "Height",
  weight: "Weight",
  steps: "Daily steps",
  exercise_frequency: "Exercise",
  activity_level: "Activity",
  main_goal: "Main goal",
  weight_goal: "Weight goal",
  health_concern: "Health concern",
  eating_barriers: "What gets in the way",
  meals_per_day: "Meals a day",
  diet_pattern: "How you eat",
  allergies: "Allergies or intolerances",
  foods_avoided: "Foods to avoid",
  cuisines: "Cuisines",
  who_cooks: "Who cooks",
  weeknight_time: "Weeknight dinner",
  food_budget: "Food budget",
  eating_out: "Eating out",
  medications: "Medications",
  anything_else: "Anything else",
};
