"use client";

import { useMemo, useState } from "react";

import type { Condition } from "@/lib/types";

import { OptionRow, PrimaryButton, ScreenActions, ScreenHeading } from "../ui";
import type { ScreenProps } from "./types";

type Choice = { kind: "condition"; id: string } | { kind: "option"; id: string } | null;

function fromValue(value: unknown): Choice {
  if (typeof value === "string") return { kind: "option", id: value };
  if (value && typeof value === "object" && "condition_id" in value) return { kind: "condition", id: String(value.condition_id) };
  return null;
}

/** Pick one condition from the catalog, with a filter. Matching from free text comes in a later step. */
export function ConditionScreen({ screen, initial, onSubmit, busy, conditions }: ScreenProps & { conditions: Condition[] }) {
  const [choice, setChoice] = useState<Choice>(() => fromValue(initial));
  const [filter, setFilter] = useState("");
  const shown = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return needle ? conditions.filter((c) => c.label.toLowerCase().includes(needle)) : conditions;
  }, [conditions, filter]);
  const headingId = `${screen.id}-heading`;

  return (
    <>
      <ScreenHeading id={headingId} title={screen.title} subtitle="Pick one from the list." />
      <input
        type="search"
        aria-label="Filter conditions"
        placeholder="Filter the list"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-3 min-h-12 rounded-2xl border border-line px-4 text-base"
      />
      <fieldset aria-labelledby={headingId} className="flex flex-col gap-2">
        {screen.options.map((option) => (
          <OptionRow
            key={option.id}
            type="radio"
            name={screen.id}
            checked={choice?.kind === "option" && choice.id === option.id}
            onChange={() => setChoice({ kind: "option", id: option.id })}
            label={option.label}
          />
        ))}
        {shown.map((condition) => (
          <OptionRow
            key={condition.id}
            type="radio"
            name={screen.id}
            checked={choice?.kind === "condition" && choice.id === condition.id}
            onChange={() => setChoice({ kind: "condition", id: condition.id })}
            label={condition.label}
          />
        ))}
      </fieldset>
      <ScreenActions>
        <PrimaryButton
          disabled={!choice || busy}
          onClick={() => choice && onSubmit(choice.kind === "option" ? choice.id : { condition_id: choice.id })}
        >
          Continue
        </PrimaryButton>
      </ScreenActions>
    </>
  );
}
