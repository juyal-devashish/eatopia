"use client";

import { PrimaryButton, ScreenActions, ScreenHeading } from "../ui";
import type { ScreenProps } from "./types";

/** Interstitial cards and the Health benefit screen: a message and Continue. */
export function InfoScreen({ screen, onSubmit, busy }: ScreenProps) {
  return (
    <>
      <div className="my-auto">
        <ScreenHeading title={screen.title} subtitle={screen.subtitle} />
      </div>
      <ScreenActions>
        <PrimaryButton disabled={busy} onClick={() => onSubmit({ seen: true })}>
          Continue
        </PrimaryButton>
      </ScreenActions>
    </>
  );
}
