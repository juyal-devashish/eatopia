"use client";

import { useState } from "react";

import { PrimaryButton, ScreenActions, ScreenHeading } from "../ui";
import type { ScreenProps } from "./types";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const THIS_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 100 }, (_, i) => THIS_YEAR - 13 - i);

function parts(value: unknown): { year: string; month: string; day: string } {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-");
    return { year, month: String(Number(month)), day: String(Number(day)) };
  }
  return { year: "", month: "", day: "" };
}

const select = "min-h-12 rounded-2xl border border-line bg-surface px-3 text-base";

export function DateScreen({ screen, initial, onSubmit, busy, actionLabel }: ScreenProps) {
  const [date, setDate] = useState(() => parts(initial));
  const daysInMonth = date.year && date.month ? new Date(Number(date.year), Number(date.month), 0).getDate() : 31;
  const valid = date.year && date.month && date.day && Number(date.day) <= daysInMonth;

  function submit() {
    const pad = (n: string) => n.padStart(2, "0");
    onSubmit(`${date.year}-${pad(date.month)}-${pad(date.day)}`);
  }

  return (
    <>
      <ScreenHeading title={screen.title} subtitle={screen.subtitle} />
      <fieldset className="grid grid-cols-[1.4fr_0.8fr_1fr] gap-2">
        <legend className="sr-only">{screen.title}</legend>
        <select aria-label="Month" className={select} value={date.month} onChange={(e) => setDate({ ...date, month: e.target.value })}>
          <option value="">Month</option>
          {MONTHS.map((name, i) => (
            <option key={name} value={String(i + 1)}>
              {name}
            </option>
          ))}
        </select>
        <select aria-label="Day" className={select} value={date.day} onChange={(e) => setDate({ ...date, day: e.target.value })}>
          <option value="">Day</option>
          {Array.from({ length: daysInMonth }, (_, i) => String(i + 1)).map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <select aria-label="Year" className={select} value={date.year} onChange={(e) => setDate({ ...date, year: e.target.value })}>
          <option value="">Year</option>
          {YEARS.map((y) => (
            <option key={y} value={String(y)}>
              {y}
            </option>
          ))}
        </select>
      </fieldset>
      <ScreenActions>
        <PrimaryButton disabled={!valid || busy} onClick={submit}>
          {actionLabel ?? "Continue"}
        </PrimaryButton>
      </ScreenActions>
    </>
  );
}
