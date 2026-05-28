"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useArtifacts } from "@/lib/queries";
import {
  ARTIFACT_TYPE_COLOR,
  ARTIFACT_TYPE_LABEL,
  ARTIFACT_TYPE_ORDER,
  type Artifact,
} from "@/lib/types";

const NAV = [
  { href: "/", label: "Overview", exact: true },
  { href: "/artifacts", label: "Artifacts", exact: false },
  { href: "/graph", label: "Graph", exact: false },
  { href: "/formalize", label: "Formalize", exact: false },
  { href: "/change-request", label: "Change request", exact: false },
  { href: "/consistency", label: "Consistency", exact: false },
];

function isActive(pathname: string, href: string, exact: boolean) {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();
  const { data: artifacts = [] } = useArtifacts();

  const byType = ARTIFACT_TYPE_ORDER.map((type) => ({
    type,
    items: artifacts.filter((a) => a.type === type),
  })).filter((group) => group.items.length > 0);

  return (
    <aside className="flex w-64 shrink-0 flex-col gap-4 overflow-y-auto border-r border-hairline bg-canvas-soft px-3 py-4">
      <nav className="flex flex-col gap-0.5">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              isActive(pathname, item.href, item.exact)
                ? "bg-primary text-on-primary"
                : "text-ink-mute hover:bg-hairline-cool hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-1">
        <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Workspace
        </p>
        {byType.length === 0 && (
          <p className="px-3 text-xs text-ink-faint">No artifacts yet.</p>
        )}
        {byType.map((group) => (
          <TreeSection
            key={group.type}
            type={group.type}
            items={group.items}
            pathname={pathname}
          />
        ))}
      </div>
    </aside>
  );
}

function TreeSection({
  type,
  items,
  pathname,
}: {
  type: Artifact["type"];
  items: Artifact[];
  pathname: string;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-sm text-ink-mute hover:bg-hairline-cool hover:text-ink"
      >
        <span className="text-[10px] text-ink-faint">{open ? "▾" : "▸"}</span>
        <span
          className="size-2 shrink-0 rounded-full"
          style={{ background: ARTIFACT_TYPE_COLOR[type] }}
        />
        <span className="flex-1 text-left">{ARTIFACT_TYPE_LABEL[type]}</span>
        <span className="text-xs text-ink-faint">{items.length}</span>
      </button>
      {open && (
        <ul className="ml-4 border-l border-hairline pl-2">
          {items.map((a) => {
            const active = pathname === `/artifacts/${a.id}`;
            return (
              <li key={a.id}>
                <Link
                  href={`/artifacts/${a.id}`}
                  title={a.title}
                  className={`block truncate rounded-md px-2 py-1 text-xs transition-colors ${
                    active
                      ? "bg-hairline-cool font-medium text-ink"
                      : "text-ink-mute hover:bg-hairline-cool hover:text-ink"
                  }`}
                >
                  {a.title}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
