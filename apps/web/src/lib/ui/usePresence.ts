"use client";

import { useEffect, useRef, useState } from "react";

export type PresenceState = "open" | "closed";

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Keeps an element mounted through its exit animation so popups can animate out,
 * not just in. Returns whether the node should be rendered (`mounted`) and the
 * `data-state` to stamp on it so the CSS motion layer can target enter/exit.
 *
 * `state` is derived straight from `open`: opening mounts the node and renders
 * it as "open" in a single commit. Because the motion is a CSS @keyframes (not a
 * transition), the enter animation plays from its first frame on mount — there's
 * no need to first commit a "closed" frame, and doing so would briefly fire the
 * exit animation and make the open look jerky. Closing flips to "closed" (which
 * plays the exit animation) and unmounts after `exitMs`.
 */
export function usePresence(open: boolean, exitMs = 120) {
  const [mounted, setMounted] = useState(open);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    clearTimeout(timer.current);
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMounted(true);
    } else {
      timer.current = setTimeout(() => setMounted(false), prefersReducedMotion() ? 0 : exitMs);
    }
    return () => clearTimeout(timer.current);
  }, [open, exitMs]);

  const state: PresenceState = open ? "open" : "closed";
  return { mounted, state };
}
