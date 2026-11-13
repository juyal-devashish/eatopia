"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { api, newKey } from "@/lib/api";
import type { MemberSummary, Mode } from "@/lib/types";

import { Onboarding } from "./Onboarding";
import { PhoneFrame } from "./PhoneFrame";
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
    description: "Apple Health access up front, with answers suggested for you to confirm. Arrives in the next build step.",
    available: false,
  },
];

export function DemoApp() {
  const [members, setMembers] = useState<MemberSummary[]>([]);
  const [member, setMember] = useState<string>("a");
  const [mode, setMode] = useState<Mode>("today");
  const [active, setActive] = useState<Active | null>(null);
  // The session in progress, if any, read from this browser's storage (nothing on the server render).
  const storedRaw = useSyncExternalStore(subscribe, readRaw, () => null);
  const resumable = useMemo(() => parse(storedRaw), [storedRaw]);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

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
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col items-center gap-8 min-[500px]:p-8 lg:flex-row lg:items-center lg:justify-center">
      <aside className={`w-full max-w-sm flex-col gap-6 p-5 min-[500px]:p-0 ${active ? "hidden min-[500px]:flex" : "flex"}`}>
        <div>
          <p className="text-xs font-semibold tracking-wide text-accent uppercase">Demo · synthetic data only</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">An onboarding that fills itself in</h1>
          <p className="mt-3 text-muted">
            Pick a synthetic member and an order. The phone shows the onboarding as a member would see it.
          </p>
        </div>

        {resumable && !active ? (
          <div className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-4">
            <p className="font-semibold">You have an onboarding in progress.</p>
            <PrimaryButton onClick={() => setActive(resumable)}>Continue where you left off</PrimaryButton>
          </div>
        ) : null}

        <fieldset className="flex flex-col gap-2" disabled={Boolean(active)}>
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

        <fieldset className="flex flex-col gap-2" disabled={Boolean(active)}>
          <legend className="mb-2 text-sm font-semibold">Order</legend>
          {MODES.map((m) => (
            <label
              key={m.id}
              className={`flex cursor-pointer gap-3 rounded-2xl border p-4 ${mode === m.id ? "border-accent bg-accent-soft" : "border-line bg-surface"} ${m.available ? "" : "opacity-60"}`}
            >
              <input
                type="radio"
                name="mode"
                className="mt-1 size-5 accent-accent"
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
        {active ? (
          <PrimaryButton onClick={exit}>Stop and choose again</PrimaryButton>
        ) : (
          <PrimaryButton onClick={start} disabled={starting || members.length === 0}>
            Start onboarding
          </PrimaryButton>
        )}
      </aside>

      <div className={active ? "flex w-full justify-center min-[500px]:w-auto" : "hidden min-[500px]:flex"}>
        <PhoneFrame>
          {active ? (
            <Onboarding key={active.id} sessionId={active.id} startedAt={active.startedAt} onExit={exit} />
          ) : (
            <p className="m-auto max-w-[16rem] text-center text-muted">Pick a member and an order, then start.</p>
          )}
        </PhoneFrame>
      </div>
    </main>
  );
}
