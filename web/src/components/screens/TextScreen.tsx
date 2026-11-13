"use client";

import { useState } from "react";

import { PrimaryButton, ScreenActions, ScreenHeading, SecondaryButton } from "../ui";
import type { ScreenProps } from "./types";

export function TextScreen({ screen, initial, onSubmit, busy }: ScreenProps) {
  const [text, setText] = useState(typeof initial === "string" ? initial : "");
  const headingId = `${screen.id}-heading`;
  return (
    <>
      <ScreenHeading id={headingId} title={screen.title} subtitle={screen.subtitle} />
      <textarea
        aria-labelledby={headingId}
        value={text}
        maxLength={1000}
        rows={5}
        onChange={(e) => setText(e.target.value)}
        className="rounded-2xl border border-line p-4 text-base"
      />
      <ScreenActions>
        <PrimaryButton disabled={!text.trim() || busy} onClick={() => onSubmit(text.trim())}>
          Continue
        </PrimaryButton>
        {screen.optional ? (
          <SecondaryButton disabled={busy} onClick={() => onSubmit(null)}>
            {screen.skip_label}
          </SecondaryButton>
        ) : null}
      </ScreenActions>
    </>
  );
}
