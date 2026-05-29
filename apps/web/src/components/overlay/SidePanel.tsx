"use client";

import { type ReactNode } from "react";

import { usePresence } from "@/lib/ui/usePresence";

/**
 * Slide-in aside that animates in and out. The caller supplies its own layout
 * classes (width, borders, flex). Built on `usePresence` so the panel stays
 * mounted through its exit slide before unmounting.
 */
export function SidePanel({
  open,
  children,
  className = "",
  exitMs = 180,
}: {
  open: boolean;
  children: ReactNode;
  className?: string;
  exitMs?: number;
}) {
  const { mounted, state } = usePresence(open, exitMs);

  if (!mounted) return null;

  return (
    <aside data-anim="panel-right" data-state={state} className={className}>
      {children}
    </aside>
  );
}
