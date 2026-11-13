"use client";

import { useState } from "react";

import type { MatchResult } from "@/lib/types";

/**
 * The member's own words in, a few listed options out. Suggestions are only shown; the member picks one or
 * ignores them. Nothing is sent until they ask.
 */
export function MatchBox({
  label,
  placeholder,
  buttonLabel,
  initialText = "",
  onMatch,
  onResult,
  onTextChange,
}: {
  label: string;
  placeholder: string;
  buttonLabel: string;
  initialText?: string;
  onMatch: (text: string) => Promise<MatchResult>;
  onResult: (result: MatchResult) => void;
  onTextChange?: (text: string) => void;
}) {
  const [text, setText] = useState(initialText);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function find() {
    setPending(true);
    setError(null);
    try {
      onResult(await onMatch(text.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't match that. Pick from the list instead.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1 text-sm text-muted">
        {label}
        <input
          value={text}
          maxLength={300}
          placeholder={placeholder}
          onChange={(e) => {
            setText(e.target.value);
            onTextChange?.(e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && text.trim() && !pending) {
              e.preventDefault();
              void find();
            }
          }}
          className="min-h-12 rounded-[1.25rem] border border-line bg-card px-4 text-base text-ink"
        />
      </label>
      <button
        type="button"
        disabled={!text.trim() || pending}
        onClick={find}
        className="min-h-11 self-start rounded-xl bg-accent-soft px-4 text-sm font-semibold text-accent disabled:opacity-50"
      >
        {pending ? "Matching…" : buttonLabel}
      </button>
      {error ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
