import Link from "next/link";
import type { ReactNode } from "react";

import {
  ARTIFACT_TYPE_COLOR,
  ARTIFACT_TYPE_LABEL,
  type ArtifactStatus,
  type ArtifactType,
} from "@/lib/types";

const PILL =
  "inline-flex items-center gap-1.5 rounded-full bg-canvas-soft px-2 py-0.5 text-xs font-medium text-ink-mute ring-1 ring-inset ring-hairline";

const POSITIVE_STATUS = new Set<ArtifactStatus>(["approved", "active", "applied"]);

export function TypeBadge({ type }: { type: ArtifactType }) {
  return (
    <span className={PILL}>
      <span className="size-1.5 rounded-full" style={{ background: ARTIFACT_TYPE_COLOR[type] }} />
      {ARTIFACT_TYPE_LABEL[type]}
    </span>
  );
}

export function StatusBadge({ status }: { status: ArtifactStatus }) {
  return (
    <span className={PILL}>
      <span
        className={`size-1.5 rounded-full ${POSITIVE_STATUS.has(status) ? "bg-primary" : "bg-ink-faint"}`}
      />
      {status.replace("_", " ")}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-hairline bg-canvas shadow-card ${className}`}>
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-medium tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-mute">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-hairline-strong p-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="max-w-sm text-sm text-ink-mute">{hint}</p>}
      {action}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-mute">
      <span className="size-4 animate-spin rounded-full border-2 border-hairline border-t-ink-mute" />
      {label ?? "Loading…"}
    </span>
  );
}

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none";

const BUTTON_VARIANT = {
  primary: "bg-primary text-on-primary hover:bg-primary-deep",
  secondary: "border border-hairline-strong bg-canvas text-ink hover:bg-canvas-soft",
} as const;

type Variant = keyof typeof BUTTON_VARIANT;

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: Variant;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${BUTTON_BASE} ${BUTTON_VARIANT[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function ButtonLink({
  children,
  href,
  variant = "primary",
  className = "",
}: {
  children: ReactNode;
  href: string;
  variant?: Variant;
  className?: string;
}) {
  return (
    <Link href={href} className={`${BUTTON_BASE} ${BUTTON_VARIANT[variant]} ${className}`}>
      {children}
    </Link>
  );
}
