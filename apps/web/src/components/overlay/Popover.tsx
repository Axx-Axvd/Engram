"use client";

import { useRef, type CSSProperties, type ReactNode, type RefObject } from "react";

import { useDismiss } from "@/lib/ui/useDismiss";
import { usePresence } from "@/lib/ui/usePresence";

const ORIGIN = { start: "top left", end: "top right", center: "top" } as const;

const noop = () => {};

/**
 * Animated floating surface for anchored dropdowns, popovers and context menus.
 * The caller keeps full control of positioning (its own `className` / `style`)
 * and trigger; Popover adds the enter/exit animation plus outside-click +
 * Escape dismissal. Pass `containerRef` (a wrapper holding both the trigger and
 * this menu) so clicking the trigger to toggle isn't treated as an outside
 * click; omit it and the menu's own box is used (e.g. a cursor context menu).
 */
export function Popover({
  open,
  onClose,
  children,
  className = "",
  style,
  align = "start",
  containerRef,
  dismissOnScroll = false,
  role = "menu",
  exitMs = 120,
}: {
  open: boolean;
  onClose?: () => void;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  align?: keyof typeof ORIGIN;
  containerRef?: RefObject<HTMLElement | null>;
  dismissOnScroll?: boolean;
  role?: string;
  exitMs?: number;
}) {
  const ownRef = useRef<HTMLDivElement>(null);
  const { mounted, state } = usePresence(open, exitMs);

  useDismiss(open && !!onClose, onClose ?? noop, containerRef ?? ownRef, {
    scroll: dismissOnScroll,
  });

  if (!mounted) return null;

  return (
    <div
      ref={ownRef}
      role={role}
      data-anim="pop"
      data-state={state}
      style={{ ["--anim-origin"]: ORIGIN[align], ...style } as CSSProperties}
      className={className}
    >
      {children}
    </div>
  );
}
