import type { ButtonHTMLAttributes, ReactNode } from "react";

/** The main action: a centred, deep-green pill. */
export function PrimaryButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="mx-auto min-h-14 w-full max-w-[17rem] rounded-full bg-accent px-6 text-[17px] font-semibold text-white shadow-[0_8px_20px_-8px_rgb(46_74_66/0.6)] disabled:cursor-not-allowed disabled:bg-disabled disabled:text-disabled-ink disabled:shadow-none"
    >
      {children}
    </button>
  );
}

/** A quiet text action under the main one, such as "Add this later". */
export function SecondaryButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="mx-auto min-h-11 px-5 text-[15px] font-semibold text-muted hover:text-ink disabled:opacity-50"
    >
      {children}
    </button>
  );
}

/** The footer of every screen: the main action, then an optional secondary one. */
export function ScreenActions({ children }: { children: ReactNode }) {
  return <div className="mt-auto flex flex-col gap-1 pt-6">{children}</div>;
}

export function ScreenHeading({ title, subtitle, id }: { title: string; subtitle?: string | null; id?: string }) {
  return (
    <div className="mb-6">
      <h1 id={id} className="font-serif text-[32px] leading-[1.12] font-medium tracking-[-0.01em]">
        {title}
      </h1>
      {subtitle ? <p className="mt-3 text-[17px] leading-snug text-muted">{subtitle}</p> : null}
    </div>
  );
}

/**
 * A tappable row built on a real radio or checkbox, so screen readers announce the group correctly. The input is
 * styled as the round check on the right.
 */
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
      className={`flex min-h-[3.75rem] cursor-pointer items-center gap-3 rounded-[1.25rem] border-2 px-5 py-3 text-[17px] has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${
        checked ? "border-accent bg-accent-soft font-semibold" : "border-transparent bg-card shadow-[0_1px_2px_rgb(29_42_36/0.05)]"
      }`}
    >
      <span className="flex-1">{label}</span>
      {hint}
      <input type={type} name={name} checked={checked} onChange={onChange} className="option-check" />
    </label>
  );
}
