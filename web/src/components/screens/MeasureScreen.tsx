"use client";

import { useState } from "react";

import { cmToFeetInches, feetInchesToCm, kgToLb, lbToKg } from "@/lib/units";

import { PrimaryButton, ScreenActions, ScreenHeading, SecondaryButton } from "../ui";
import type { ScreenProps } from "./types";

const UNIT_LABELS: Record<string, string> = { ft_in: "Feet and inches", cm: "Centimetres", lb: "Pounds", kg: "Kilograms" };
const field = "min-h-14 w-full rounded-[1.25rem] border border-line bg-card px-4 text-xl font-semibold";

function stored(value: unknown, key: "cm" | "kg"): number | null {
  if (value && typeof value === "object" && key in value) {
    const n = (value as Record<string, unknown>)[key];
    return typeof n === "number" ? n : null;
  }
  return null;
}

/** Height or weight, in either unit. The API always receives cm or kg. */
export function MeasureScreen({ screen, initial, onSubmit, busy, actionLabel }: ScreenProps) {
  const height = screen.kind === "height";
  const [unit, setUnit] = useState(screen.units[0]);
  const start = stored(initial, height ? "cm" : "kg");
  const startFtIn = start !== null && height ? cmToFeetInches(start) : null;
  const [feet, setFeet] = useState(startFtIn ? String(startFtIn.feet) : "");
  const [inches, setInches] = useState(startFtIn ? String(startFtIn.inches) : "");
  const [amount, setAmount] = useState(start === null ? "" : String(height ? start : kgToLb(start)));

  function value(): { cm: number } | { kg: number } | null {
    if (height) {
      if (unit === "ft_in") {
        if (feet === "" || inches === "") return null;
        return { cm: feetInchesToCm(Number(feet), Number(inches)) };
      }
      return amount === "" ? null : { cm: Number(amount) };
    }
    if (amount === "") return null;
    return { kg: unit === "lb" ? lbToKg(Number(amount)) : Number(amount) };
  }

  function switchUnit(next: string) {
    const current = value();
    if (current && "cm" in current && next === "ft_in") {
      const { feet: f, inches: i } = cmToFeetInches(current.cm);
      setFeet(String(f));
      setInches(String(i));
    } else if (current && "cm" in current) {
      setAmount(String(current.cm));
    } else if (current && "kg" in current) {
      setAmount(String(next === "lb" ? kgToLb(current.kg) : current.kg));
    }
    setUnit(next);
  }

  const result = value();
  return (
    <>
      <ScreenHeading title={screen.title} subtitle={screen.subtitle} />
      <div role="radiogroup" aria-label="Unit" className="mb-5 grid grid-cols-2 gap-2">
        {screen.units.map((u) => (
          <button
            key={u}
            type="button"
            role="radio"
            aria-checked={unit === u}
            onClick={() => switchUnit(u)}
            className={`min-h-12 rounded-full text-[15px] font-semibold ${unit === u ? "bg-ink text-white" : "bg-disabled text-muted"}`}
          >
            {UNIT_LABELS[u] ?? u}
          </button>
        ))}
      </div>
      {height && unit === "ft_in" ? (
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm text-muted">
            Feet
            <input inputMode="numeric" type="number" min={3} max={8} value={feet} onChange={(e) => setFeet(e.target.value)} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-sm text-muted">
            Inches
            <input inputMode="numeric" type="number" min={0} max={11} value={inches} onChange={(e) => setInches(e.target.value)} className={field} />
          </label>
        </div>
      ) : (
        <label className="flex flex-col gap-1 text-sm text-muted">
          {UNIT_LABELS[unit]}
          <input inputMode="decimal" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} className={field} />
        </label>
      )}
      <ScreenActions>
        <PrimaryButton disabled={!result || busy} onClick={() => result && onSubmit(result)}>
          {actionLabel ?? "Continue"}
        </PrimaryButton>
        {screen.optional ? (
          <SecondaryButton disabled={busy} onClick={() => onSubmit(null)}>
            {screen.skip_label}
          </SecondaryButton>
        ) : null}
      </ScreenActions>
    </>
  );
}
