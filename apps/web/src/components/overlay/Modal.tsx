"use client";

import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { usePresence } from "@/lib/ui/usePresence";

/**
 * Centered dialog with a fading backdrop, portalled to <body>. Backdrop click
 * and Escape close it, and body scroll is locked while open. No consumer today;
 * the shared primitive future dialogs should build on so they animate for free.
 */
export function Modal({
  open,
  onClose,
  children,
  className = "",
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const { mounted, state } = usePresence(open, 140);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!mounted || typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div
        data-anim="fade"
        data-state={state}
        onClick={onClose}
        className="absolute inset-0 bg-black/40 backdrop-blur-[1px]"
      />
      <div
        role="dialog"
        aria-modal="true"
        data-anim="modal"
        data-state={state}
        className={`relative max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-hairline bg-canvas shadow-deep ${className}`}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
