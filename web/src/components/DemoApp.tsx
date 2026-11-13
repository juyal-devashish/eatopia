"use client";

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { api, newKey } from "@/lib/api";
import type { Form, MemberSummary, Mode, SessionState } from "@/lib/types";

import { AppShell } from "./AppShell";
import { BehindTheScenes } from "./BehindTheScenes";
import { Onboarding } from "./Onboarding";
import { PrimaryButton } from "./ui";

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

// The demo shows one scenario: a synthetic member whose watch has recorded everything, with Health first.
const MEMBER = "a";
const MODE: Mode = "health_first";

export function DemoApp() {
  const [members, setMembers] = useState<MemberSummary[]>([]);
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
      const session = await api.createSession(MEMBER, MODE, newKey());
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

  const member = members.find((m) => m.id === MEMBER);

  return (
    <div className="flex min-h-dvh w-full items-center justify-center gap-8">
    <AppShell>
      {active ? (
        <Onboarding key={active.id} sessionId={active.id} startedAt={active.startedAt} onExit={exit} onUpdate={onUpdate} />
      ) : (
        <main className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-5 pt-8 pb-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-accent uppercase">Independent demo · synthetic data only</p>
            <h1 className="mt-2 font-serif text-[34px] leading-[1.1] font-medium">An onboarding that fills itself in</h1>
            <p className="mt-2 text-muted">
              Apple Health fills in what it already knows. A few spoken sentences fill in most of the rest. You confirm
              every answer, with far fewer taps than a form.
            </p>
          </div>

          {resumable ? (
            <div className="flex flex-col gap-3 rounded-[1.25rem] bg-card p-4">
              <p className="font-semibold">You have an onboarding in progress.</p>
              <PrimaryButton onClick={() => setActive(resumable)}>Continue where you left off</PrimaryButton>
            </div>
          ) : null}

          {member ? (
            <div className="rounded-[1.25rem] bg-card p-4">
              <p className="text-sm font-semibold">You&apos;ll go through as a synthetic member</p>
              <p className="mt-1 text-sm text-muted">
                {member.label}: {member.description}
              </p>
            </div>
          ) : null}

          {error ? (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          ) : null}
          <div className="mt-auto flex flex-col">
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
