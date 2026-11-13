"use client";

import type { Form, SessionState } from "@/lib/types";

import { PrimaryButton, SecondaryButton } from "./ui";

function duration(ms: number | null): string {
  if (ms === null) return "–";
  const seconds = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}

/**
 * The end of the run: what it asked of the member, next to what the same questions take asked one per screen.
 * That baseline is the fewest taps each screen could take, so the comparison can only understate the saving.
 */
export function FinishScreen({
  session,
  baseline,
  startedAt,
  finishedAt,
  onDietitian,
  onExit,
}: {
  session: SessionState;
  baseline: Form["baseline"];
  startedAt: number;
  finishedAt: number | null;
  onDietitian: () => void;
  onExit: () => void;
}) {
  const ms = finishedAt === null ? null : finishedAt - startedAt;
  const { stats } = session;
  const rows: [string, string, string][] = [
    ["Screens", String(stats.screens_seen), String(baseline.screens)],
    ["Taps", String(session.tap_count), `${baseline.min_taps}+`],
    ["Filled for you", String(stats.filled_from_health + stats.estimates_taken + stats.filled_from_voice), "0"],
  ];

  return (
    <div data-testid="finish" className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 pt-8 pb-6">
      <div>
        <h1 tabIndex={-1} className="font-serif text-[32px] font-medium">
          You&apos;re all set
        </h1>
        <p className="mt-1 text-muted">A dietitian would now review these answers.</p>
      </div>

      <table data-testid="comparison" className="w-full text-sm">
        <caption className="mb-2 text-left font-semibold">What this onboarding took</caption>
        <thead>
          <tr className="text-left text-muted">
            <th scope="col" className="font-normal" />
            <th scope="col" className="font-semibold text-ink">
              This run
            </th>
            <th scope="col" className="font-semibold text-ink">
              One per screen*
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, run, base]) => (
            <tr key={label} className="border-t border-line">
              <th scope="row" className="py-2 text-left font-normal text-muted">
                {label}
              </th>
              <td data-testid={`run-${label}`} className="py-2 text-xl font-semibold">
                {run}
              </td>
              <td data-testid={`baseline-${label}`} className="py-2 text-xl font-semibold text-muted">
                {base}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3} className="pt-2 text-xs text-muted">
              *The same questions with Apple Health asked later and nothing filled in, counting the fewest taps each
              screen could take. Time for this run: {duration(ms)}.
            </td>
          </tr>
        </tfoot>
      </table>

      <p className="text-sm text-muted" data-testid="from-health">
        From Apple Health: {stats.filled_from_health} answers filled for you
        {stats.estimates_taken ? `, ${stats.estimates_taken} suggestions used` : ""}
        {stats.changed_from_health ? `, ${stats.changed_from_health} changed by you` : ""}.
        {stats.filled_from_voice ? ` From what you said: ${stats.filled_from_voice} answers filled in.` : ""}
      </p>

      <div className="mt-auto flex flex-col gap-2">
        <PrimaryButton onClick={onDietitian}>See what the dietitian gets</PrimaryButton>
        <SecondaryButton onClick={onExit}>Start again</SecondaryButton>
      </div>
    </div>
  );
}
