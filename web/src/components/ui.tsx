import type { ButtonHTMLAttributes, ReactNode } from "react";

export function PrimaryButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="min-h-12 w-full rounded-2xl bg-accent px-5 text-base font-semibold text-white disabled:cursor-not-allowed disabled:bg-line disabled:text-muted"
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="min-h-11 w-full rounded-2xl px-5 text-sm font-semibold text-accent underline-offset-4 hover:underline"
    >
      {children}
    </button>
  );
}

/** The fixed footer of every screen: the main action, then an optional secondary one. */
export function ScreenActions({ children }: { children: ReactNode }) {
  return <div className="mt-auto flex flex-col gap-2 pt-4">{children}</div>;
}

export function ScreenHeading({ title, subtitle, id }: { title: string; subtitle?: string | null; id?: string }) {
  return (
    <div className="mb-5">
      <h1 id={id} className="text-[26px] leading-tight font-semibold tracking-tight">
        {title}
      </h1>
      {subtitle ? <p className="mt-2 text-base text-muted">{subtitle}</p> : null}
    </div>
  );
}

/** A tappable row built on a real radio or checkbox, so screen readers announce the group correctly. */
export function OptionRow({
  type,
  name,
  checked,
  onChange,
  label,
  hint,
}: {
  type: "radio" | "checkbox";
  name: string;
  checked: boolean;
  onChange: () => void;
  label: string;
  hint?: ReactNode;
}) {
  return (
    <label
      className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-base has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-accent ${
        checked ? "border-accent bg-accent-soft font-semibold" : "border-line bg-surface"
      }`}
    >
      <input type={type} name={name} checked={checked} onChange={onChange} className="size-5 shrink-0 accent-accent" />
      <span className="flex-1">{label}</span>
      {hint}
    </label>
  );
}
