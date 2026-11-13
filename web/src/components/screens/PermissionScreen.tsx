"use client";

import { PrimaryButton, ScreenActions, SecondaryButton } from "../ui";
import type { ScreenProps } from "./types";

const READ_TYPE_LABELS: Record<string, string> = {
  HKCharacteristicTypeIdentifierBiologicalSex: "Sex",
  HKCharacteristicTypeIdentifierDateOfBirth: "Date of birth",
  HKQuantityTypeIdentifierHeight: "Height",
  HKQuantityTypeIdentifierBodyMass: "Weight",
  HKQuantityTypeIdentifierStepCount: "Steps",
  HKWorkoutTypeIdentifier: "Workouts",
  HKCategoryTypeIdentifierSleepAnalysis: "Sleep",
};

/** A stand-in for the iPhone's Health permission sheet. Clearly labelled as simulated. */
export function PermissionScreen({ screen, onSubmit, busy }: ScreenProps) {
  return (
    <>
      <div className="my-auto rounded-3xl border border-line bg-page p-5">
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">Simulated permission</p>
        <h1 className="mt-2 text-xl font-semibold">Allow this app to read from Apple Health?</h1>
        <p className="mt-2 text-sm text-muted">On a real iPhone this is the system sheet. Here it uses a synthetic member&apos;s data.</p>
        <ul className="mt-4 flex flex-col gap-1.5 text-base">
          {screen.read_types.map((type) => (
            <li key={type} className="flex items-center gap-2">
              <span aria-hidden className="size-2 rounded-full bg-accent" />
              {READ_TYPE_LABELS[type] ?? type}
            </li>
          ))}
        </ul>
      </div>
      <ScreenActions>
        <PrimaryButton disabled={busy} onClick={() => onSubmit({ granted: true })}>
          Allow
        </PrimaryButton>
        <SecondaryButton disabled={busy} onClick={() => onSubmit({ granted: false })}>
          Don&apos;t allow
        </SecondaryButton>
      </ScreenActions>
    </>
  );
}
