"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { formatAnswer, SHORT_LABELS } from "@/lib/format";
import type { Condition, Form, SessionState, SummaryResult } from "@/lib/types";

import { SecondaryButton } from "./ui";

const SOURCE: Record<string, { label: string; className: string }> = {
  health_confirmed: { label: "From Health, confirmed", className: "bg-accent-soft text-accent" },
  health_changed: { label: "From Health, changed", className: "bg-warn-soft text-warn-ink" },
  voice_confirmed: { label: "From what they said, confirmed", className: "bg-accent-soft text-ink" },
  member: { label: "Entered by member", className: "bg-page text-muted" },
};

const NON_QUESTIONS = new Set(["interstitial", "health_benefit", "health_permission", "health_review", "voice"]);

/** What a dietitian would read: a short summary, then every answer with where it came from. */
export function DietitianView({
  session,
  form,
  conditions,
  onBack,
}: {
  session: SessionState;
  form: Form;
  conditions: Condition[];
  onBack: () => void;
}) {
  const [summary, setSummary] = useState<SummaryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // A fixed key per session: reopening this view returns the stored summary instead of calling the model again.
    api.summary(session.id, `summary-${session.id}`).then(
      (result) => {
        if (!cancelled) setSummary(result);
      },
      (e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Couldn't load the summary");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [session.id]);

  const questions = form.screens.filter((s) => !NON_QUESTIONS.has(s.kind) && s.id in session.answers);

  return (
    <div data-testid="dietitian" className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 pt-6 pb-6">
      <div>
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">Dietitian view · synthetic member {session.member_id.toUpperCase()}</p>
        <h1 className="mt-1 font-serif text-[30px] font-medium">Intake record</h1>
      </div>

      <section aria-labelledby="summary-heading" className="rounded-[1.25rem] bg-card p-4">
        <h2 id="summary-heading" className="text-sm font-semibold">
          Summary
        </h2>
        {summary ? (
          <>
            <p data-testid="summary-text" className="mt-2 text-base">
              {summary.text}
            </p>
            <p className="mt-2 text-xs text-muted">
              {summary.status === "ok"
                ? `${summary.written_by_model ? `Written by ${summary.writer ?? "the model"}` : "Written by the offline stand-in, not a model,"} from the member's own answers. ${
                    summary.health_values_filled.length
                      ? `Health values (${summary.health_values_filled.map((n) => SHORT_LABELS[n] ?? n).join(", ").toLowerCase()}) were filled in by code afterwards.`
                      : "No Health values were needed."
                  }`
                : "No model summary for this intake."}
            </p>
          </>
        ) : error ? (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {error}
          </p>
        ) : (
          <p className="mt-2 text-muted">Writing the summary…</p>
        )}
      </section>

      {form.sections.map((section) => {
        const inSection = questions.filter((q) => q.section === section.id);
        if (!inSection.length) return null;
        return (
          <section key={section.id} aria-labelledby={`dv-${section.id}`}>
            <h2 id={`dv-${section.id}`} className="mb-2 text-xs font-semibold tracking-wide text-muted uppercase">
              {section.title}
              {section.assumed ? " (illustrative)" : ""}
            </h2>
            <dl className="flex flex-col divide-y divide-line rounded-[1.25rem] bg-card">
              {inSection.map((q) => {
                const answer = session.answers[q.id];
                const source = SOURCE[answer.source];
                return (
                  <div key={q.id} data-answer={q.id} className="flex flex-col gap-1 p-3">
                    <dt className="text-sm text-muted">{q.title}</dt>
                    <dd className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold">{formatAnswer(q, answer.value, conditions)}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${source.className}`}>{source.label}</span>
                    </dd>
                  </div>
                );
              })}
            </dl>
          </section>
        );
      })}

      <SecondaryButton onClick={onBack}>Back</SecondaryButton>
    </div>
  );
}
