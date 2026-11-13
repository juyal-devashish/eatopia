"use client";

import { useEffect, useRef, useState } from "react";

import { formatAnswer, SHORT_LABELS } from "@/lib/format";
import type { AnswerValue, Condition, ExtractResult, Screen } from "@/lib/types";

import { ScreenView } from "../ScreenView";
import { PrimaryButton, ScreenActions, ScreenHeading, SecondaryButton } from "../ui";

/** How fast the simulated dictation appears, per word. */
const WORD_MS = 70;

type Phase = "idle" | "listening" | "filling" | "review";

interface VoiceProps {
  screen: Screen;
  /** The questions this screen covers, from the schema. */
  covered: Screen[];
  /** What the synthetic member "says" when the mic is tapped. */
  script: string | undefined;
  /** Earlier answers, when the member comes back with Back. */
  earlier: Record<string, AnswerValue>;
  conditions: Condition[];
  onExtract: (text: string) => Promise<ExtractResult>;
  onSubmit: (value: AnswerValue) => void;
  busy: boolean;
}

function isCondition(value: AnswerValue): boolean {
  return Boolean(value && typeof value === "object" && "condition_id" in value);
}

/**
 * One spoken answer fills several questions. Dictation is simulated: the mic plays a synthetic script into the
 * transcript, as on-device speech recognition would on an iPhone. The member can edit it or type instead. Claude
 * turns the text into answers; each is shown for the member to confirm, change, or choose when it wasn't said.
 * A matched health condition is a suggestion and needs its own tap.
 */
export function VoiceScreen({ screen, covered, script, earlier, conditions, onExtract, onSubmit, busy }: VoiceProps) {
  const resumed = covered.some((q) => q.id in earlier);
  const [phase, setPhase] = useState<Phase>(resumed ? "review" : "idle");
  const [transcript, setTranscript] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, AnswerValue>>(() =>
    Object.fromEntries(covered.map((q) => [q.id, earlier[q.id] ?? null])),
  );
  const [heard, setHeard] = useState<Set<string>>(new Set());
  const [checked, setChecked] = useState<Set<string>>(() => new Set(resumed ? covered.map((q) => q.id) : []));
  const [editing, setEditing] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => () => {
    if (timer.current !== null) window.clearInterval(timer.current);
  }, []);

  async function fill(text: string) {
    setPhase("filling");
    setProblem(null);
    setSent(text);
    try {
      const result = await onExtract(text);
      const answers = Object.fromEntries(covered.map((q) => [q.id, result.answers[q.id] ?? null]));
      setValues(answers);
      setHeard(new Set(covered.filter((q) => answers[q.id] !== null).map((q) => q.id)));
      setChecked(new Set());
      if (result.status !== "ok") setProblem("We couldn't fill these in from that. Choose each one below.");
    } catch (e) {
      setProblem(e instanceof Error ? e.message : "Something went wrong. Choose each one below.");
    }
    setPhase("review");
  }

  function speak() {
    if (!script) return;
    const words = script.split(" ");
    let shown = 0;
    setTranscript("");
    setPhase("listening");
    timer.current = window.setInterval(() => {
      shown += 1;
      setTranscript(words.slice(0, shown).join(" "));
      if (shown >= words.length) {
        window.clearInterval(timer.current!);
        timer.current = null;
        void fill(script);
      }
    }, WORD_MS);
  }

  if (editing) {
    const target = covered.find((q) => q.id === editing)!;
    return (
      <div className="flex flex-1 flex-col">
        <ScreenView
          screen={target}
          initial={values[editing] ?? undefined}
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

  // A matched condition is only a suggestion; a required question nobody answered still needs a choice.
  const unconfirmed = covered.filter((q) => isCondition(values[q.id]) && heard.has(q.id) && !checked.has(q.id));
  const missing = covered.filter((q) => !q.optional && values[q.id] === null);
  const ready = phase === "review" && unconfirmed.length === 0 && missing.length === 0;
  const edited = transcript.trim() !== "" && transcript.trim() !== sent;

  return (
    <>
      <ScreenHeading title={screen.title} subtitle={screen.subtitle} />

      <div className="rounded-3xl bg-card p-4 shadow-[0_1px_3px_rgb(29_42_36/0.08)]">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold tracking-wide text-muted uppercase">Simulated: voice</p>
          {phase === "listening" ? (
            <p role="status" className="flex items-center gap-2 text-sm font-semibold text-accent">
              <span aria-hidden className="size-2 animate-pulse rounded-full bg-accent" />
              Listening…
            </p>
          ) : phase === "filling" ? (
            <p role="status" className="text-sm font-semibold text-accent">
              Filling in your answers…
            </p>
          ) : null}
        </div>
        <label htmlFor={`${screen.id}-said`} className="sr-only">
          What you said
        </label>
        <textarea
          id={`${screen.id}-said`}
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          readOnly={phase === "listening" || phase === "filling"}
          rows={4}
          placeholder={script ? "Tap the mic and speak, or type here." : "Type your answer here."}
          className="mt-2 w-full resize-none rounded-2xl border border-line bg-surface p-3 text-base leading-snug"
        />
        <div className="mt-3 flex items-center gap-3">
          {script ? (
            <button
              type="button"
              onClick={speak}
              disabled={phase === "listening" || phase === "filling"}
              aria-label="Speak (simulated)"
              className="grid size-14 shrink-0 place-items-center rounded-full bg-accent text-white shadow-[0_8px_20px_-8px_rgb(46_74_66/0.6)] disabled:bg-disabled disabled:text-disabled-ink"
            >
              <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="3" width="6" height="11" rx="3" />
                <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
              </svg>
            </button>
          ) : null}
          <p className="flex-1 text-xs text-muted">
            {script
              ? "On an iPhone this is on-device dictation. Here, the mic plays what a synthetic member says."
              : "Say it in your own words; we'll fill in what we can."}
          </p>
        </div>
        {edited && phase !== "listening" && phase !== "filling" ? (
          <button
            type="button"
            onClick={() => void fill(transcript.trim())}
            className="mt-3 min-h-11 w-full rounded-full bg-surface text-sm font-semibold text-accent ring-1 ring-line"
          >
            {sent ? "Update my answers" : "Fill in my answers"}
          </button>
        ) : null}
      </div>

      {phase === "review" ? (
        <section aria-labelledby={`${screen.id}-heard`} className="mt-5">
          <h2 id={`${screen.id}-heard`} className="mb-2 font-semibold">
            {sent ? "From what you said" : "Your answers"}
          </h2>
          {problem ? (
            <p role="alert" className="mb-2 text-sm text-warn-ink">
              {problem}
            </p>
          ) : null}
          <ul className="flex flex-col gap-2">
            {covered.map((q) => {
              const value = values[q.id];
              const label = SHORT_LABELS[q.id] ?? q.title;
              const flagged = unconfirmed.includes(q);
              const empty = value === null;
              const action = empty ? (q.optional ? "Add" : "Choose") : "Change";
              return (
                <li
                  key={q.id}
                  data-voice-row={q.id}
                  className={`rounded-2xl border p-3.5 ${flagged || (empty && !q.optional) ? "border-warn-ink/40 bg-warn-soft" : "border-transparent bg-card"}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm text-muted">{label}</p>
                      <p className={empty ? "text-base text-muted" : "text-base font-semibold"}>
                        {empty ? (q.optional ? "Nothing added" : "Not mentioned") : formatAnswer(q, value, conditions)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEditing(q.id)}
                      aria-label={`${action} ${label}`}
                      className="min-h-11 shrink-0 rounded-xl px-3 text-sm font-semibold text-accent"
                    >
                      {action}
                    </button>
                  </div>
                  {flagged ? (
                    <div className="mt-2 flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-warn-ink">Is this the right condition?</p>
                      <button
                        type="button"
                        onClick={() => setChecked((c) => new Set(c).add(q.id))}
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
        </section>
      ) : null}

      <ScreenActions>
        <PrimaryButton disabled={!ready || busy} onClick={() => onSubmit({ rows: values })}>
          {phase !== "review" ? "Confirm" : unconfirmed.length || missing.length ? "Check highlighted answers" : "Confirm"}
        </PrimaryButton>
        {phase === "idle" ? (
          <SecondaryButton onClick={() => setPhase("review")}>Answer each one instead</SecondaryButton>
        ) : null}
      </ScreenActions>
    </>
  );
}
