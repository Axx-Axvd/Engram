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
    <aside className="flex w-64 shrink-0 flex-col gap-4 overflow-y-auto border-r border-neutral-200 bg-neutral-50/60 px-3 py-4 dark:border-neutral-800 dark:bg-neutral-950">
      <nav className="flex flex-col gap-0.5">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive(pathname, item.href, item.exact)
                ? "bg-indigo-600 text-white"
                : "text-neutral-600 hover:bg-neutral-200/60 dark:text-neutral-300 dark:hover:bg-neutral-800"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-1">
        <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-neutral-400">
          Workspace
        </p>
        {byType.length === 0 && (
          <p className="px-3 text-xs text-neutral-400">No artifacts yet.</p>
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
        className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-200/60 dark:text-neutral-300 dark:hover:bg-neutral-800"
      >
        <span className="text-[10px] text-neutral-400">{open ? "▾" : "▸"}</span>
        <span
          className="size-2 shrink-0 rounded-full"
          style={{ background: ARTIFACT_TYPE_COLOR[type] }}
        />
        <span className="flex-1 text-left">{ARTIFACT_TYPE_LABEL[type]}</span>
        <span className="text-xs text-neutral-400">{items.length}</span>
      </button>
      {open && (
        <ul className="ml-4 border-l border-neutral-200 pl-2 dark:border-neutral-800">
          {items.map((a) => {
            const active = pathname === `/artifacts/${a.id}`;
            return (
              <li key={a.id}>
                <Link
                  href={`/artifacts/${a.id}`}
                  title={a.title}
                  className={`block truncate rounded-md px-2 py-1 text-xs transition-colors ${
                    active
                      ? "bg-neutral-200 font-medium text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
                      : "text-neutral-500 hover:bg-neutral-200/60 dark:hover:bg-neutral-800"
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
