"use client";

import { useState } from "react";

import type { Option } from "@/lib/types";

import { OptionRow, PrimaryButton, ScreenActions, ScreenHeading } from "../ui";
import type { ScreenProps } from "./types";

type Picked = Record<string, string>; // option id -> free text ("" for ordinary options)

function fromValue(value: unknown): Picked {
  const items = Array.isArray(value) ? value : value === undefined || value === null ? [] : [value];
  const picked: Picked = {};
  for (const item of items) {
    if (typeof item === "string") picked[item] = "";
    else if (item && typeof item === "object" && "option" in item && "text" in item) {
      picked[String(item.option)] = String(item.text);
    }
  }
  return picked;
}

function toItem(option: Option, picked: Picked): unknown {
  return option.free_text ? { option: option.id, text: picked[option.id].trim() } : option.id;
}

export function ChoiceScreen({ screen, initial, onSubmit, busy, suggestion, actionLabel }: ScreenProps) {
  const multi = screen.kind === "multi_choice";
  const [picked, setPicked] = useState<Picked>(() => fromValue(initial));
  const headingId = `${screen.id}-heading`;

  function toggle(option: Option) {
    setPicked((current) => {
      if (!multi) return { [option.id]: current[option.id] ?? "" };
      const next = { ...current };
      if (option.id in next) {
        delete next[option.id];
        return next;
      }
      if (option.exclusive) return { [option.id]: "" };
      for (const other of screen.options) if (other.exclusive) delete next[other.id];
      next[option.id] = "";
      return next;
    });
  }

  // An estimate is highlighted, never selected: the member taps to choose it.
  const hinted = suggestion && suggestion.kind === "estimate" && suggestion.status !== "ask" ? suggestion.value : null;
  const chosen = screen.options.filter((o) => o.id in picked);
  const missingText = chosen.some((o) => o.free_text && !picked[o.id].trim());
  const ready = chosen.length > 0 && !missingText;

  function submit() {
    const items = chosen.map((o) => toItem(o, picked));
    onSubmit(multi ? items : items[0]);
  }

  return (
    <>
      <fieldset aria-labelledby={headingId} className="flex flex-col gap-2.5">
        <legend className="contents">
          <ScreenHeading id={headingId} title={screen.title} subtitle={screen.subtitle} />
        </legend>
        {screen.options.map((option) => (
          <div key={option.id} className="flex flex-col gap-2">
            <OptionRow
              type={multi ? "checkbox" : "radio"}
              name={screen.id}
              checked={option.id in picked}
              onChange={() => toggle(option)}
              label={option.label}
              hint={
                hinted === option.id ? (
                  <span className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">Suggested</span>
                ) : undefined
              }
            />
            {option.free_text && option.id in picked ? (
              <input
                aria-label={`${option.label}: tell us more`}
                value={picked[option.id]}
                maxLength={300}
                onChange={(event) => setPicked((p) => ({ ...p, [option.id]: event.target.value }))}
                placeholder="Tell us more"
                className="min-h-12 rounded-2xl border border-line px-4 text-base"
              />
            ) : null}
          </div>
        ))}
      </fieldset>
      <ScreenActions>
        <PrimaryButton disabled={!ready || busy} onClick={submit}>
          {actionLabel ?? "Continue"}
        </PrimaryButton>
      </ScreenActions>
    </>
  );
}
