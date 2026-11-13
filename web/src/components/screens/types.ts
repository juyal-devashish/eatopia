import type { AnswerValue, RuleResult, Screen } from "@/lib/types";

export interface ScreenProps {
  screen: Screen;
  /** The member's earlier answer, when they come back to this screen. */
  initial: AnswerValue | undefined;
  onSubmit: (value: AnswerValue) => void;
  busy: boolean;
  /** The Health rule's result for this screen, in Health first. */
  suggestion?: RuleResult;
  /** Label for the main button; the review card's editors say "Use this". */
  actionLabel?: string;
}
