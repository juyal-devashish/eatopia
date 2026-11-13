"use client";

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { api, newKey } from "@/lib/api";
import type { Form, MemberSummary, Mode, SessionState } from "@/lib/types";

import { AppShell } from "./AppShell";
import { BehindTheScenes } from "./BehindTheScenes";
import { Onboarding } from "./Onboarding";
import { OptionRow, PrimaryButton } from "./ui";

const STORAGE_KEY = "intake-demo-session";

interface Active {
  id: string;
  startedAt: number;
}

function readRaw(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function parse(raw: string | null): Active | null {
  try {
    return raw ? (JSON.parse(raw) as Active) : null;
  } catch {
    return null;
  }
}

function store(active: Active | null) {
  try {
    if (active) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(active));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be blocked; the demo still works, it just can't resume after a reload.
  }
}

const MODES: { id: Mode; label: string; description: string; available: boolean }[] = [
  {
    id: "today",
    label: "Today's order",
    description: "Every question asked. Apple Health access is requested in section 3.",
    available: true,
  },
  {
    id: "health_first",
    label: "Health first",
    description: "Apple Health access up front, with answers suggested for you to confirm.",
    available: true,
  },
];

export function DemoApp() {
  const [members, setMembers] = useState<MemberSummary[]>([]);
  const [member, setMember] = useState<string>("a");
  const [mode, setMode] = useState<Mode>("today");
  const [active, setActive] = useState<Active | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [view, setView] = useState<{ session: SessionState; form: Form } | null>(null);
  const onUpdate = useCallback((session: SessionState, form: Form) => setView({ session, form }), []);
  // The session in progress, if any, read from this browser's storage (nothing on the server render).
  const storedRaw = useSyncExternalStore(subscribe, readRaw, () => null);
  const resumable = useMemo(() => parse(storedRaw), [storedRaw]);

  useEffect(() => {
    api.members().then(setMembers, () => setError("The API isn't reachable. Is the backend running?"));
  }, []);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const session = await api.createSession(member, mode, newKey());
      const next = { id: session.id, startedAt: Date.now() };
      store(next);
      setActive(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start");
    } finally {
      setStarting(false);
    }
  }

  function exit() {
    store(null);
    setActive(null);
    setView(null);
  }

  return (
    <div className="flex min-h-dvh w-full items-center justify-center gap-8">
    <AppShell>
      {active ? (
        <Onboarding key={active.id} sessionId={active.id} startedAt={active.startedAt} onExit={exit} onUpdate={onUpdate} />
      ) : (
        <main className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-5 pt-8 pb-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-accent uppercase">Demo · synthetic data only</p>
            <h1 className="mt-2 text-[28px] leading-tight font-semibold tracking-tight">An onboarding that fills itself in</h1>
            <p className="mt-2 text-muted">Pick a synthetic member and an order, then go through onboarding as they would.</p>
          </div>

          {resumable ? (
            <div className="flex flex-col gap-3 rounded-2xl border border-line bg-page p-4">
              <p className="font-semibold">You have an onboarding in progress.</p>
              <PrimaryButton onClick={() => setActive(resumable)}>Continue where you left off</PrimaryButton>
            </div>
          ) : null}

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-sm font-semibold">Synthetic member</legend>
            {members.map((m) => (
              <OptionRow
                key={m.id}
                type="radio"
                name="member"
                checked={member === m.id}
                onChange={() => setMember(m.id)}
                label={`${m.id.toUpperCase()}: ${m.label}`}
                hint={<span className="sr-only">{m.description}</span>}
              />
            ))}
            <p className="text-sm text-muted">{members.find((m) => m.id === member)?.description}</p>
          </fieldset>

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-sm font-semibold">Order</legend>
            {MODES.map((m) => (
              <label
                key={m.id}
                className={`flex cursor-pointer gap-3 rounded-2xl border p-4 has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-accent ${mode === m.id ? "border-accent bg-accent-soft" : "border-line bg-surface"} ${m.available ? "" : "opacity-60"}`}
              >
                <input
                  type="radio"
                  name="mode"
                  className="mt-1 size-5 shrink-0 accent-accent"
                  checked={mode === m.id}
                  disabled={!m.available}
                  onChange={() => setMode(m.id)}
                />
                <span>
                  <span className="block font-semibold">{m.label}</span>
                  <span className="block text-sm text-muted">{m.description}</span>
                </span>
              </label>
            ))}
          </fieldset>

          {error ? (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          ) : null}
          <div className="mt-auto">
            <PrimaryButton onClick={start} disabled={starting || members.length === 0}>
              Start onboarding
            </PrimaryButton>
          </div>
        </main>
      )}
    </AppShell>
      {active && view ? (
        <aside aria-label="Behind the scenes" tabIndex={0} className="hidden h-[min(932px,100dvh)] w-[380px] shrink-0 overflow-y-auto py-8 lg:block">
          <BehindTheScenes session={view.session} form={view.form} />
        </aside>
      ) : null}
    </div>
  );
}
