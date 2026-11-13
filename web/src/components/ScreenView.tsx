"use client";

import type { Condition } from "@/lib/types";

import { ChoiceScreen } from "./screens/ChoiceScreen";
import { ConditionScreen } from "./screens/ConditionScreen";
import { DateScreen } from "./screens/DateScreen";
import { InfoScreen } from "./screens/InfoScreen";
import { MeasureScreen } from "./screens/MeasureScreen";
import { PermissionScreen } from "./screens/PermissionScreen";
import { TextScreen } from "./screens/TextScreen";
import type { ScreenProps } from "./screens/types";

/** Picks the component for a screen kind. One component per kind, all driven by the question schema. */
export function ScreenView(props: ScreenProps & { conditions: Condition[] }) {
  switch (props.screen.kind) {
    case "single_choice":
    case "multi_choice":
      return <ChoiceScreen {...props} />;
    case "date":
      return <DateScreen {...props} />;
    case "height":
    case "weight":
      return <MeasureScreen {...props} />;
    case "text":
      return <TextScreen {...props} />;
    case "interstitial":
    case "health_benefit":
      return <InfoScreen {...props} />;
    case "health_permission":
      return <PermissionScreen {...props} />;
    case "condition_picker":
      return <ConditionScreen {...props} />;
    case "health_review":
      return null; // rendered by Onboarding, which has the rows and suggestions
  }
}
