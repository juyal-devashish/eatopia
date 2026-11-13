"use client";

import { useMemo, useState } from "react";

import type { Condition, MatchResult } from "@/lib/types";

import { OptionRow, PrimaryButton, ScreenActions, ScreenHeading } from "../ui";
import { MatchBox } from "./MatchBox";
import type { ScreenProps } from "./types";

type Choice = { kind: "condition"; id: string } | { kind: "option"; id: string } | null;

function fromValue(value: unknown): Choice {
  if (typeof value === "string") return { kind: "option", id: value };
  if (value && typeof value === "object" && "condition_id" in value) return { kind: "condition", id: String(value.condition_id) };
  return null;
}

/**
 * One health concern: describe it in your own words and pick from the closest matches, or browse the list.
 * Matches are suggestions only; nothing is selected for the member.
 */
export function ConditionScreen({
  screen,
  initial,
  onSubmit,
  busy,
  conditions,
  onMatch,
  actionLabel,
}: ScreenProps & { conditions: Condition[] }) {
  const [choice, setChoice] = useState<Choice>(() => fromValue(initial));
  const [result, setResult] = useState<MatchResult | null>(null);
  const [showList, setShowList] = useState(() => !onMatch || fromValue(initial)?.kind === "condition");
  const [filter, setFilter] = useState("");
  const shown = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return needle ? conditions.filter((c) => c.label.toLowerCase().includes(needle)) : conditions;
  }, [conditions, filter]);
  const headingId = `${screen.id}-heading`;
  const noMatch = result !== null && (result.show_full_list || result.matches.length === 0);

  function pick(id: string) {
    setChoice({ kind: "condition", id });
  }

  return (
    <>
      <ScreenHeading id={headingId} title={screen.title} subtitle={screen.subtitle} />
      {onMatch ? (
        <MatchBox
          label="In your own words"
          placeholder="For example: my sugar was high at my last check-up"
          buttonLabel="Find matches"
          onMatch={onMatch}
          onResult={(r) => {
            setResult(r);
            if (r.show_full_list || r.matches.length === 0) setShowList(true);
          }}
        />
      ) : null}

      {result && result.matches.length > 0 ? (
        <fieldset className="mt-4 flex flex-col gap-2">
          <legend className="mb-2 text-sm font-semibold">Closest matches. Pick one if it fits.</legend>
          {result.matches.map((m) => (
            <OptionRow
              key={m.id}
              type="radio"
              name={screen.id}
              checked={choice?.kind === "condition" && choice.id === m.id}
              onChange={() => pick(m.id)}
              label={m.label}
            />
          ))}
        </fieldset>
      ) : null}
      {noMatch ? (
        <p role="status" className="mt-3 text-sm text-muted">
          We couldn&apos;t match that to the list. Pick from it below, or choose no specific condition.
        </p>
      ) : null}

      <fieldset aria-labelledby={headingId} className="mt-4 flex flex-col gap-2">
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
      </fieldset>

      <button
        type="button"
        aria-expanded={showList}
        onClick={() => setShowList((open) => !open)}
        className="mt-3 min-h-11 self-start text-sm font-semibold text-accent"
      >
        {showList ? "Hide the full list" : "Browse the full list"}
      </button>
      {showList ? (
        <div className="flex flex-col gap-2">
          <input
            type="search"
            aria-label="Filter conditions"
            placeholder="Filter the list"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="min-h-12 rounded-[1.25rem] border border-line bg-card px-4 text-base"
          />
          <fieldset aria-label="All conditions" className="flex flex-col gap-2">
            {shown.map((condition) => (
              <OptionRow
                key={condition.id}
                type="radio"
                name={screen.id}
                checked={choice?.kind === "condition" && choice.id === condition.id}
                onChange={() => pick(condition.id)}
                label={condition.label}
              />
            ))}
          </fieldset>
        </div>
      ) : null}

      <ScreenActions>
        <PrimaryButton
          disabled={!choice || busy}
          onClick={() => choice && onSubmit(choice.kind === "option" ? choice.id : { condition_id: choice.id })}
        >
          {actionLabel ?? "Continue"}
        </PrimaryButton>
      </ScreenActions>
    </>
  );
}
