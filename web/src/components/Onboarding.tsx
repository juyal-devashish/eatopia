"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, newKey } from "@/lib/api";
import type { AnswerValue, Condition, Form, RuleResult, SessionState } from "@/lib/types";

import { BehindTheScenes } from "./BehindTheScenes";
import { DietitianView } from "./DietitianView";
import { FinishScreen } from "./FinishScreen";
import { ReviewScreen } from "./screens/ReviewScreen";
import { ScreenView } from "./ScreenView";
import { PrimaryButton, SecondaryButton } from "./ui";

interface Props {
  sessionId: string;
  startedAt: number;
  onExit: () => void;
  /** Lets the page show the Behind the scenes panel beside the app on wide screens. */
  onUpdate: (session: SessionState, form: Form) => void;
}

/** One line above a Health-linked question saying what Apple Health contributed, or why it couldn't. */
function HealthNote({ suggestion }: { suggestion: RuleResult | undefined }) {
  if (!suggestion) return null;
  const text =
    suggestion.status === "ask"
      ? `Apple Health couldn't answer this. ${suggestion.evidence}.`
      : suggestion.kind === "estimate"
        ? `Suggested from Apple Health: ${suggestion.evidence}. Tap it if it's right.`
        : `From Apple Health: ${suggestion.evidence}.`;
  return <p className="mb-3 rounded-xl bg-accent-soft px-3 py-2 text-sm text-ink">{text}</p>;
}

export function Onboarding({ sessionId, startedAt, onExit, onUpdate }: Props) {
  const [session, setSession] = useState<SessionState | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [viewing, setViewing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finishedAt, setFinishedAt] = useState<number | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [finishView, setFinishView] = useState<"summary" | "dietitian">("summary");
  const taps = useRef(0);
  const screenRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const state = await api.session(sessionId);
        const [schema, catalog] = await Promise.all([api.form(state.mode), api.conditions()]);
        if (cancelled) return;
        setSession(state);
        setForm(schema);
        setConditions(catalog);
        // After a reload, Back walks through the screens already answered, in flow order.
        setHistory(schema.screens.filter((s) => s.id in state.answers).map((s) => s.id));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load the session");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const currentId = viewing ?? session?.next_screen_id ?? null;

  useEffect(() => {
    if (session && form) onUpdate(session, form);
  }, [session, form, onUpdate]);

  // Move focus to the new screen so keyboard and screen-reader users start at its heading.
  useEffect(() => {
    screenRef.current?.focus({ preventScroll: true });
  }, [currentId]);

  const submit = useCallback(
    async (screenId: string, value: AnswerValue) => {
      setBusy(true);
      setError(null);
      try {
        // One key per submission: a retry inside api.answer reuses it, so the answer is saved once.
        const next = await api.answer(sessionId, screenId, value, newKey(), taps.current);
        taps.current = 0;
        setHistory((h) => [...h, screenId]);
        setViewing(null);
        setSession(next);
        if (next.finished) setFinishedAt(Date.now());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong. Try again.");
      } finally {
        setBusy(false);
      }
    },
    [sessionId],
  );

  function back() {
    const previous = history.at(-1);
    if (!previous) return;
    setHistory((h) => h.slice(0, -1));
    setViewing(previous);
  }

  if (error && !session) {
    return (
      <div className="flex flex-1 flex-col justify-center gap-4 p-6">
        <p role="alert">{error}</p>
        <PrimaryButton onClick={onExit}>Start again</PrimaryButton>
      </div>
    );
  }
  if (!session || !form) return <p className="m-auto text-muted">Loading…</p>;

  if (currentId === null) {
    if (finishView === "dietitian") {
      return <DietitianView session={session} form={form} conditions={conditions} onBack={() => setFinishView("summary")} />;
    }
    return (
      <FinishScreen
        session={session}
        baseline={form.baseline}
        startedAt={startedAt}
        finishedAt={finishedAt}
        onDietitian={() => setFinishView("dietitian")}
        onExit={onExit}
      />
    );
  }

  const screens = form.screens;
  const screen = screens.find((s) => s.id === currentId);
  if (!screen) return <p className="m-auto text-muted">Unknown screen {currentId}</p>;
  const index = screens.indexOf(screen);
  const section = form.sections.find((s) => s.id === screen.section);
  const progress = Math.round((index / screens.length) * 100);
  // One bar segment per section, filled as the member moves through it.
  const segments = form.sections.map((sec) => {
    const inSection = screens.filter((s) => s.section === sec.id);
    const done = inSection.filter((s) => screens.indexOf(s) < index).length;
    return { id: sec.id, fill: inSection.length ? done / inSection.length : 0 };
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 justify-end gap-4 px-5 pt-1 text-[13px] font-semibold text-muted">
        <button
          type="button"
          onClick={() => setShowPanel((open) => !open)}
          aria-expanded={showPanel}
          className="min-h-9 hover:text-ink lg:hidden"
        >
          Details
        </button>
        <button type="button" onClick={onExit} className="min-h-9 hover:text-ink">
          Exit
        </button>
      </div>
      <div className="flex shrink-0 items-center gap-3 px-5 pb-4">
        <button
          type="button"
          onClick={back}
          disabled={history.length === 0 || busy}
          aria-label="Back"
          className="grid size-12 shrink-0 place-items-center rounded-full bg-card text-xl text-ink shadow-[0_1px_3px_rgb(29_42_36/0.08)] disabled:opacity-40"
        >
          ‹
        </button>
        <div
          role="progressbar"
          aria-label="Progress"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          className="flex flex-1 gap-1.5"
        >
          {segments.map((seg) => (
            <div key={seg.id} className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
              <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(seg.fill * 100)}%` }} />
            </div>
          ))}
        </div>
        <p className="shrink-0 text-right text-[13px] font-semibold text-muted">
          {section?.title}
          {section?.assumed ? <span className="sr-only"> (illustrative)</span> : null}
        </p>
      </div>
      <div
        key={screen.id}
        ref={screenRef}
        tabIndex={-1}
        data-screen-id={screen.id}
        data-kind={screen.kind}
        onClickCapture={() => {
          taps.current += 1;
        }}
        className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-6 outline-none"
      >
        {showPanel ? (
          <div className="flex flex-col gap-4 lg:hidden">
            <BehindTheScenes session={session} form={form} />
            <SecondaryButton onClick={() => setShowPanel(false)}>Back to onboarding</SecondaryButton>
          </div>
        ) : screen.kind === "health_review" ? (
          <ReviewScreen
            screen={screen}
            rows={session.review_rows}
            suggestions={session.suggestions}
            screensById={Object.fromEntries(form.screens.map((s) => [s.id, s]))}
            earlier={Object.fromEntries(
              session.review_rows.filter((row) => row in session.answers).map((row) => [row, session.answers[row].value]),
            )}
            conditions={conditions}
            initial={undefined}
            onSubmit={(value) => submit(screen.id, value)}
            busy={busy}
          />
        ) : (
          <>
            <HealthNote suggestion={session.suggestions[screen.id]} />
            <ScreenView
              screen={screen}
              initial={session.answers[screen.id]?.value}
              onSubmit={(value) => submit(screen.id, value)}
              busy={busy}
              conditions={conditions}
              suggestion={session.suggestions[screen.id]}
              onMatch={
                screen.kind === "condition_picker"
                  ? (text) => api.matchCondition(sessionId, text, newKey())
                  : screen.options.some((o) => o.free_text)
                    ? (text) => api.matchOption(sessionId, screen.id, text, newKey())
                    : undefined
              }
            />
          </>
        )}
        {error ? (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
}
