import type { AnswerValue, Screen } from "@/lib/types";

export interface ScreenProps {
  screen: Screen;
  /** The member's earlier answer, when they come back to this screen. */
  initial: AnswerValue | undefined;
  onSubmit: (value: AnswerValue) => void;
  busy: boolean;
}
