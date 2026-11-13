import type { MemberId, Mode, RunStats } from "./types";

/** Finished runs in this browser, so the finish screen can compare the two orders for the same member. */
export interface Run extends RunStats {
  sessionId: string;
  member: MemberId;
  mode: Mode;
  taps: number;
  ms: number;
  finishedAt: number;
}

const KEY = "intake-demo-runs";

export function loadRuns(): Run[] {
  try {
    return JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as Run[];
  } catch {
    return [];
  }
}

export function saveRun(run: Run): void {
  try {
    const others = loadRuns().filter((r) => r.sessionId !== run.sessionId);
    window.localStorage.setItem(KEY, JSON.stringify([...others, run].slice(-20)));
  } catch {
    // Storage can be blocked; the comparison just won't appear.
  }
}

/** The latest finished run for this member in the other order. */
export function counterpart(run: Run, runs: Run[]): Run | null {
  const other = runs.filter((r) => r.member === run.member && r.mode !== run.mode);
  return other.length ? other[other.length - 1] : null;
}
