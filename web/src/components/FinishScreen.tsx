"use client";

import { useEffect, useMemo, useState } from "react";

import { counterpart, loadRuns, type Run, saveRun } from "@/lib/runs";
import type { SessionState } from "@/lib/types";

import { PrimaryButton, SecondaryButton } from "./ui";

function duration(ms: number | null): string {
  if (ms === null) return "–";
  const seconds = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}

const MODE_LABEL = { today: "Today's order", health_first: "Health first" } as const;

/**
 * The end of a run: what it asked of the member. Once the same member has run both orders in this browser, the
 * two appear side by side, counts first; time comes last because a second run is always faster.
 */
export function FinishScreen({
  session,
  startedAt,
  finishedAt,
  onDietitian,
  onExit,
}: {
  session: SessionState;
  startedAt: number;
  finishedAt: number | null;
  onDietitian: () => void;
  onExit: () => void;
}) {
  const ms = finishedAt === null ? null : finishedAt - startedAt;
  const run = useMemo<Run | null>(
    () =>
      ms === null
        ? null
        : {
            ...session.stats,
            sessionId: session.id,
            member: session.member_id,
            mode: session.mode,
            taps: session.tap_count,
            ms,
            finishedAt: finishedAt ?? 0,
          },
    [session, ms, finishedAt],
  );
  const [earlier] = useState(loadRuns);
  const other = run ? counterpart(run, earlier) : null;

  useEffect(() => {
    if (run) saveRun(run);
  }, [run]);

  const fromHealth = session.stats.filled_from_health + session.stats.estimates_taken;
  const columns = other && run ? (run.mode === "today" ? [run, other] : [other, run]) : null;

  return (
    <div data-testid="finish" className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 pt-8 pb-6">
      <div>
        <h1 tabIndex={-1} className="font-serif text-[32px] font-medium">
          You&apos;re all set
        </h1>
        <p className="mt-1 text-muted">A dietitian would now review these answers.</p>
      </div>

      <dl className="grid grid-cols-3 gap-2 rounded-[1.25rem] bg-card p-4 text-center">
        <div>
          <dt className="text-xs text-muted">Screens</dt>
          <dd data-testid="screens-seen" className="text-xl font-semibold">
            {session.stats.screens_seen}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Taps</dt>
          <dd className="text-xl font-semibold">{session.tap_count}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Time</dt>
          <dd className="text-xl font-semibold">{duration(ms)}</dd>
        </div>
      </dl>
      {session.mode === "health_first" ? (
        <p className="text-sm text-muted" data-testid="from-health">
          From Apple Health: {session.stats.filled_from_health} answers filled for you
          {session.stats.estimates_taken ? `, ${session.stats.estimates_taken} suggestions used` : ""}
          {session.stats.changed_from_health ? `, ${session.stats.changed_from_health} changed by you` : ""}.
        </p>
      ) : null}

      {columns ? (
        <table data-testid="comparison" className="w-full text-sm">
          <caption className="mb-2 text-left font-semibold">Member {session.member_id.toUpperCase()}, both orders</caption>
          <thead>
            <tr className="text-left text-muted">
              <th scope="col" className="font-normal" />
              {columns.map((c) => (
                <th key={c.mode} scope="col" className="font-semibold text-ink">
                  {MODE_LABEL[c.mode]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["Screens", (c: Run) => String(c.screens_seen)],
              ["Taps", (c: Run) => String(c.taps)],
              ["From Apple Health", (c: Run) => String(c.filled_from_health + c.estimates_taken)],
              ["Time*", (c: Run) => duration(c.ms)],
            ].map(([label, cell]) => (
              <tr key={label as string} className="border-t border-line">
                <th scope="row" className="py-2 text-left font-normal text-muted">
                  {label as string}
                </th>
                {columns.map((c) => (
                  <td key={c.mode} className="py-2 font-semibold">
                    {(cell as (c: Run) => string)(c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="pt-2 text-xs text-muted">
                *A second run is always faster because you already know the questions. Counts are the fairer guide.
              </td>
            </tr>
          </tfoot>
        </table>
      ) : (
        <p className="text-sm text-muted">
          {fromHealth || session.mode === "health_first"
            ? "Try the same member in Today's order to compare."
            : "Try the same member in Health first to compare."}
        </p>
      )}

      <div className="mt-auto flex flex-col gap-2">
        <PrimaryButton onClick={onDietitian}>See what the dietitian gets</PrimaryButton>
        <SecondaryButton onClick={onExit}>Try another member or order</SecondaryButton>
      </div>
    </div>
  );
}
