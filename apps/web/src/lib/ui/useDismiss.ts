"use client";

import { useEffect, type RefObject } from "react";

/**
 * Shared "close on outside click / Escape" behaviour for floating surfaces,
 * replacing the near-identical effect that each popup used to hand-roll. The
 * `ref` should point at the element (or wrapper) that counts as "inside" — for
 * a toggle button + menu pair, pass the wrapper so clicking the trigger doesn't
 * register as an outside click and fight the toggle.
 */
export function useDismiss(
  open: boolean,
  onClose: () => void,
  ref: RefObject<HTMLElement | null>,
  opts?: { scroll?: boolean },
) {
  const scroll = opts?.scroll ?? false;

  useEffect(() => {
    if (!open) return;

    const onPointer = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("mousedown", onPointer, true);
    document.addEventListener("keydown", onKey, true);
    if (scroll) {
      window.addEventListener("scroll", onClose, true);
      window.addEventListener("resize", onClose);
    }
    return () => {
      document.removeEventListener("mousedown", onPointer, true);
      document.removeEventListener("keydown", onKey, true);
      if (scroll) {
        window.removeEventListener("scroll", onClose, true);
        window.removeEventListener("resize", onClose);
      }
    };
  }, [open, onClose, ref, scroll]);
}
