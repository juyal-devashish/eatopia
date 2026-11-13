"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { daysAgo, formatAnswer, formatDate, formatHeight, formatWeight, SHORT_LABELS } from "@/lib/format";
import type { EgressEntry, Form, RuleResult, SessionState } from "@/lib/types";

const STATUS: Record<RuleResult["status"], string> = {
  suggested: "Suggested",
  needs_check: "Needs a check",
  ask: "Asked",
};

const SOURCE: Record<string, string> = {
  health_confirmed: "from Health, confirmed",
  health_changed: "from Health, changed",
  member: "entered by member",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{title}</h3>
      {children}
    </section>
  );
}

/**
 * What happens behind the onboarding: the member's Health data, what each rule did with it, and every request
 * sent to the model, word for word.
 */
export function BehindTheScenes({ session, form }: { session: SessionState; form: Form }) {
  const [egress, setEgress] = useState<EgressEntry[]>([]);
  const answered = Object.keys(session.answers).length;

  useEffect(() => {
    let cancelled = false;
    api.egress(session.id).then(
      (entries) => {
        if (!cancelled) setEgress(entries);
      },
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
  }, [session.id, answered]);

  const summary = session.health_summary;
  const linked = form.screens.filter((s) => s.health);
  const stepDays = summary?.daily_steps_30d.length ?? 0;

  return (
    <div className="flex flex-col gap-6 text-sm">
      <div>
        <h2 className="text-lg font-semibold">Behind the scenes</h2>
        <p className="text-muted">
          {session.mode === "today"
            ? "Today's order: Apple Health is requested, but no answer comes from it."
            : "Health first: plain code turns Apple Health data into suggestions. The model never sees these values."}
        </p>
      </div>

      {session.mode === "health_first" ? (
        <Section title="Apple Health data (this member's own)">
          {summary ? (
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-xl bg-page p-3">
              <dt className="text-muted">Sex</dt>
              <dd>{summary.biological_sex ?? "not set"}</dd>
              <dt className="text-muted">Date of birth</dt>
              <dd>{summary.date_of_birth ? formatDate(summary.date_of_birth) : "not set"}</dd>
              <dt className="text-muted">Height</dt>
              <dd>
                {summary.latest_height ? `${formatHeight(Math.round(summary.latest_height.value * 1000) / 10)}, ${daysAgo(summary.latest_height.at)}` : "none"}
              </dd>
              <dt className="text-muted">Weight</dt>
              <dd>{summary.latest_weight ? `${formatWeight(Math.round(summary.latest_weight.value * 10) / 10)}, ${daysAgo(summary.latest_weight.at)}` : "none"}</dd>
              <dt className="text-muted">Workouts</dt>
              <dd>
                {summary.workouts_last_28d} in the last 4 weeks ({summary.workouts_recorded} recorded)
              </dd>
              <dt className="text-muted">Steps</dt>
              <dd>{stepDays} of the last 30 days have data</dd>
            </dl>
          ) : (
            <p className="text-muted">None yet. Access hasn&apos;t been granted, was denied, or Apple Health is empty.</p>
          )}
        </Section>
      ) : null}

      {session.mode === "health_first" ? (
        <Section title="What each rule did">
          <ul className="flex flex-col gap-2">
            {linked.map((screen) => {
              const result = session.suggestions[screen.id];
              const answer = session.answers[screen.id];
              return (
                <li key={screen.id} className="rounded-xl border border-line p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{SHORT_LABELS[screen.id] ?? screen.title}</span>
                    <span className="rounded-full bg-page px-2 py-0.5 text-xs font-semibold">
                      {result ? `${STATUS[result.status]} · ${result.kind}` : "Waiting for access"}
                    </span>
                  </div>
                  {result ? <p className="mt-1 text-muted">{result.evidence}</p> : null}
                  {answer ? (
                    <p className="mt-1">
                      Answer: {formatAnswer(screen, answer.value)} <span className="text-muted">({SOURCE[answer.source]})</span>
                    </p>
                  ) : null}
                  {result ? <p className="mt-1 font-mono text-xs text-muted">{`${result.rule} ${result.version}`}</p> : null}
                </li>
              );
            })}
          </ul>
        </Section>
      ) : null}

      <Section title="What the model saw">
        {egress.length === 0 ? (
          <p className="text-muted">
            No model calls yet. Claude is only used when the member describes a health concern in their own words.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {egress.map((entry) => (
              <li key={entry.id}>
                <details className="rounded-xl border border-line p-3">
                  <summary className="cursor-pointer font-semibold">
                    {entry.purpose} · {entry.status}
                    {entry.latency_ms !== null ? ` · ${(entry.latency_ms / 1000).toFixed(1)} s` : ""}
                  </summary>
                  {entry.request ? (
                    <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-page p-2 text-xs whitespace-pre-wrap">
                      {[entry.request.system, ...(entry.request.messages ?? []).map((m) => `[${m.role}]\n${m.content}`)]
                        .filter(Boolean)
                        .join("\n\n")}
                    </pre>
                  ) : (
                    <p className="mt-2 text-muted">Nothing was sent ({entry.status}).</p>
                  )}
                  {entry.result ? <pre className="mt-2 rounded-lg bg-page p-2 text-xs whitespace-pre-wrap">{JSON.stringify(entry.result, null, 2)}</pre> : null}
                  {entry.error ? <p className="mt-2 text-muted">{entry.error}</p> : null}
                </details>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
