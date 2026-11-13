"use client";

import { useState } from "react";

import { daysAgo, formatAnswer, SHORT_LABELS } from "@/lib/format";
import type { AnswerValue, Condition, RuleResult, Screen } from "@/lib/types";

import { ScreenView } from "../ScreenView";
import { PrimaryButton, ScreenActions, ScreenHeading, SecondaryButton } from "../ui";
import type { ScreenProps } from "./types";

interface ReviewProps extends ScreenProps {
  rows: string[];
  suggestions: Record<string, RuleResult>;
  screensById: Record<string, Screen>;
  earlier: Record<string, AnswerValue>;
  conditions: Condition[];
}

/**
 * "From Apple Health": every answer Health can give, on one card. Each row can be changed in place. Facts are
 * filled in; estimates (exercise, activity) and rows with weak data need their own tap before Confirm works, so
 * confirming everything at once can't accept a guess unread.
 */
export function ReviewScreen({ screen, rows, suggestions, screensById, earlier, conditions, onSubmit, busy }: ReviewProps) {
  const [values, setValues] = useState<Record<string, AnswerValue>>(() =>
    Object.fromEntries(rows.map((row) => [row, row in earlier ? earlier[row] : suggestions[row].value])),
  );
  const [checked, setChecked] = useState<Set<string>>(() => new Set(rows.filter((row) => row in earlier)));
  const [editing, setEditing] = useState<string | null>(null);

  const tapFirst = (row: string) => suggestions[row].status === "needs_check" || suggestions[row].kind === "estimate";
  const needsCheck = rows.filter((row) => tapFirst(row) && !checked.has(row));

  if (editing) {
    const target = screensById[editing];
    return (
      <div className="flex flex-1 flex-col">
        <ScreenView
          screen={target}
          initial={values[editing]}
          onSubmit={(value) => {
            setValues((v) => ({ ...v, [editing]: value }));
            setChecked((c) => new Set(c).add(editing));
            setEditing(null);
          }}
          busy={false}
          conditions={conditions}
          actionLabel="Use this"
        />
        <SecondaryButton onClick={() => setEditing(null)}>Cancel</SecondaryButton>
      </div>
    );
  }

  return (
    <>
      <ScreenHeading title={screen.title} subtitle={screen.subtitle} />
      <ul className="flex flex-col gap-2.5">
        {rows.map((row) => {
          const suggestion = suggestions[row];
          const flagged = tapFirst(row) && !checked.has(row);
          const estimate = suggestion.kind === "estimate" && suggestion.status !== "needs_check";
          const changed = JSON.stringify(values[row]) !== JSON.stringify(suggestion.value);
          return (
            <li
              key={row}
              data-row={row}
              className={`rounded-2xl border p-4 ${flagged ? (estimate ? "border-accent/40 bg-accent-soft" : "border-warn-ink/40 bg-warn-soft") : "border-transparent bg-card"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-muted">{SHORT_LABELS[row] ?? row}</p>
                  <p className="text-lg font-semibold">{formatAnswer(screensById[row], values[row])}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setEditing(row)}
                  aria-label={`Change ${SHORT_LABELS[row] ?? row}`}
                  className="min-h-11 shrink-0 rounded-xl px-3 text-sm font-semibold text-accent"
                >
                  Change
                </button>
              </div>
              <p className="mt-1 text-xs text-muted">
                {changed ? "Changed by you" : suggestion.evidence}
                {!changed && suggestion.observed_at && !suggestion.evidence.includes(" ago") ? ` · ${daysAgo(suggestion.observed_at)}` : ""}
              </p>
              {flagged ? (
                <div className="mt-3 flex items-center justify-between gap-3">
                  <p className={`text-sm font-semibold ${estimate ? "text-accent" : "text-warn-ink"}`}>
                    {estimate ? "Suggested from your activity. Is it right?" : "Please check this one"}
                  </p>
                  <button
                    type="button"
                    onClick={() => setChecked((c) => new Set(c).add(row))}
                    className="min-h-11 rounded-xl bg-surface px-3 text-sm font-semibold text-ink ring-1 ring-line"
                  >
                    Looks right
                  </button>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
      <ScreenActions>
        <PrimaryButton disabled={needsCheck.length > 0 || busy} onClick={() => onSubmit({ rows: values })}>
          {needsCheck.length > 0 ? "Check highlighted answers" : "Confirm"}
        </PrimaryButton>
      </ScreenActions>
    </>
  );
}
