import type { ReactNode } from "react";

/**
 * The app is built for phones. On a phone it fills the screen; on a wider screen it keeps a phone's width and
 * proportions (430 x 932 at most) in the middle of the page, with no device frame.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh w-full items-center justify-center">
      <div className="flex h-dvh w-full max-w-[430px] flex-col bg-surface pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] min-[500px]:h-[min(932px,100dvh)] min-[500px]:border-x min-[500px]:border-line min-[500px]:shadow-sm">
        {children}
      </div>
    </div>
  );
}
