"use client";

import { useEffect, useState } from "react";

import { READ_TYPE_LABELS } from "./PermissionScreen";

/** How long the sync screen stays up at least, so the member sees where their answers come from. */
export const HEALTH_SYNC_MS = 2_500;

/**
 * Shown between the permission sheet and the review card while the app "reads" Apple Health. Simulated: the
 * synthetic member's data is already on the server; this paces it the way a real HealthKit read would feel.
 */
export function HealthSyncScreen({ readTypes }: { readTypes: string[] }) {
  const [done, setDone] = useState(0);
  const step = HEALTH_SYNC_MS / (readTypes.length + 1);

  useEffect(() => {
    const timer = window.setInterval(() => setDone((n) => Math.min(n + 1, readTypes.length)), step);
    return () => window.clearInterval(timer);
  }, [readTypes.length, step]);

  const finished = done === readTypes.length;

  return (
    <div data-testid="health-sync" className="flex flex-1 flex-col justify-center px-5 pb-6">
      <div className="rounded-3xl bg-card p-5 shadow-[0_1px_3px_rgb(29_42_36/0.08)]">
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">Simulated: Apple Health</p>
        <h1 className="mt-2 font-serif text-2xl font-medium">Reading your Apple Health data</h1>
        <p role="status" className="mt-2 text-sm text-muted">
          {finished ? "Filling in your answers…" : `Reading ${(READ_TYPE_LABELS[readTypes[done]] ?? readTypes[done]).toLowerCase()}…`}
        </p>
        <ul className="mt-4 flex flex-col gap-2 text-base">
          {readTypes.map((type, i) => (
            <li key={type} className="flex items-center gap-3">
              {i < done ? (
                <span aria-hidden className="grid size-6 place-items-center rounded-full bg-accent text-sm text-white">
                  ✓
                </span>
              ) : (
                <span
                  aria-hidden
                  className={`size-6 rounded-full border-2 border-line ${i === done ? "animate-spin border-t-accent" : ""}`}
                />
              )}
              <span className={i < done ? "" : "text-muted"}>{READ_TYPE_LABELS[type] ?? type}</span>
              <span className="sr-only">{i < done ? "read" : "waiting"}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
