"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, newKey } from "@/lib/api";
import type { AnswerValue, Condition, Form, SessionState } from "@/lib/types";

import { ScreenView } from "./ScreenView";
import { PrimaryButton } from "./ui";

interface Props {
  sessionId: string;
  startedAt: number;
  onExit: () => void;
}

function formatDuration(ms: number): string {
  const seconds = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}

export function Onboarding({ sessionId, startedAt, onExit }: Props) {
  const [session, setSession] = useState<SessionState | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [viewing, setViewing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finishedAt, setFinishedAt] = useState<number | null>(null);
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
    return (
      <div data-testid="finish" className="flex flex-1 flex-col gap-4 p-6">
        <h1 tabIndex={-1} className="mt-auto text-[26px] font-semibold">You&apos;re all set</h1>
        <p className="text-muted">A dietitian would now review these answers.</p>
        <dl className="grid grid-cols-3 gap-2 rounded-2xl bg-page p-4 text-center">
          <div>
            <dt className="text-xs text-muted">Screens</dt>
            <dd data-testid="screens-answered" className="text-xl font-semibold">{Object.keys(session.answers).length}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Taps</dt>
            <dd className="text-xl font-semibold">{session.tap_count}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Time</dt>
            <dd className="text-xl font-semibold">{finishedAt === null ? "–" : formatDuration(finishedAt - startedAt)}</dd>
          </div>
        </dl>
        <div className="mt-auto">
          <PrimaryButton onClick={onExit}>Try another member or mode</PrimaryButton>
        </div>
      </div>
    );
  }

  const screens = form.screens;
  const screen = screens.find((s) => s.id === currentId);
  if (!screen) return <p className="m-auto text-muted">Unknown screen {currentId}</p>;
  const index = screens.indexOf(screen);
  const section = form.sections.find((s) => s.id === screen.section);
  const progress = Math.round((index / screens.length) * 100);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center gap-3 px-5 pt-2 pb-3">
        <button
          type="button"
          onClick={back}
          disabled={history.length === 0 || busy}
          aria-label="Back"
          className="grid size-11 shrink-0 place-items-center rounded-full bg-page text-lg disabled:opacity-40"
        >
          ‹
        </button>
        <div className="flex-1">
          <div
            role="progressbar"
            aria-label="Progress"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-1.5 overflow-hidden rounded-full bg-line"
          >
            <div className="h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-1 text-xs font-semibold text-muted">
            {section?.title}
            {section?.assumed ? " · illustrative" : ""}
          </p>
        </div>
        <button type="button" onClick={onExit} className="min-h-11 px-1 text-sm font-semibold text-accent min-[500px]:hidden">
          Exit
        </button>
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
        <ScreenView
          screen={screen}
          initial={session.answers[screen.id]?.value}
          onSubmit={(value) => submit(screen.id, value)}
          busy={busy}
          conditions={conditions}
        />
        {error ? (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
}
