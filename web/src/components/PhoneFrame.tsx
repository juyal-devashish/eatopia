import type { ReactNode } from "react";

/**
 * A phone-sized frame on wide screens. On a real phone (under 500 px) the frame drops away and the
 * content fills the screen.
 */
export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh w-full flex-col bg-surface min-[500px]:min-h-0 min-[500px]:h-[min(844px,calc(100dvh-4rem))] min-[500px]:w-[390px] min-[500px]:overflow-hidden min-[500px]:rounded-[48px] min-[500px]:border-[10px] min-[500px]:border-ink min-[500px]:shadow-2xl">
      <div aria-hidden className="hidden h-9 shrink-0 items-center justify-between px-7 text-xs font-semibold min-[500px]:flex">
        <span>9:41</span>
        <span className="h-4 w-20 rounded-full bg-ink" />
        <span>100%</span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
