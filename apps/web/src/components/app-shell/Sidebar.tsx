"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { useDismiss } from "@/lib/ui/useDismiss";
import { usePresence } from "@/lib/ui/usePresence";
import { useArtifacts, useDeleteArtifact } from "@/lib/queries";
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

type Menu = { artifact: Artifact; x: number; y: number };

export function Sidebar() {
  const pathname = usePathname();
  const { data: artifacts = [] } = useArtifacts();
  const [menu, setMenu] = useState<Menu | null>(null);

  const byType = ARTIFACT_TYPE_ORDER.map((type) => ({
    type,
    items: artifacts.filter((a) => a.type === type),
  })).filter((group) => group.items.length > 0);

  function openMenu(artifact: Artifact, e: React.MouseEvent) {
    e.preventDefault();
    setMenu({ artifact, x: e.clientX, y: e.clientY });
  }

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
            onContext={openMenu}
          />
        ))}
      </div>

      <DocumentContextMenu menu={menu} onClose={() => setMenu(null)} />
    </aside>
  );
}

function TreeSection({
  type,
  items,
  pathname,
  onContext,
}: {
  type: Artifact["type"];
  items: Artifact[];
  pathname: string;
  onContext: (artifact: Artifact, e: React.MouseEvent) => void;
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
                  onContextMenu={(e) => onContext(a, e)}
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

function DocumentContextMenu({ menu, onClose }: { menu: Menu | null; onClose: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const deleteArtifact = useDeleteArtifact();
  const ref = useRef<HTMLDivElement>(null);

  const open = menu !== null;
  const { mounted, state } = usePresence(open);

  // Retain the last menu so it can finish its exit animation after `menu` clears
  // (set-state-during-render, guarded so it can't loop). Seed the position from
  // the cursor in the same pass so the menu's first paint is already in place —
  // the clamp effect below only nudges it inward near a viewport edge.
  const [m, setM] = useState<Menu | null>(menu);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  if (menu && menu !== m) {
    setM(menu);
    setPos({ x: menu.x, y: menu.y });
  }

  // Clamp inside the viewport once the element has actually mounted (presence
  // defers the mount by a frame, so we key on `mounted` rather than the coords).
  useEffect(() => {
    const el = ref.current;
    if (!el || !m) return;
    const { width, height } = el.getBoundingClientRect();
    const x = Math.min(m.x, window.innerWidth - width - 8);
    const y = Math.min(m.y, window.innerHeight - height - 8);
    setPos({ x: Math.max(8, x), y: Math.max(8, y) });
  }, [mounted, m]);

  useDismiss(open, onClose, ref, { scroll: true });

  function onDelete() {
    if (!m) return;
    const { id } = m.artifact;
    deleteArtifact.mutate(id, {
      onSuccess: () => {
        if (pathname === `/artifacts/${id}`) router.push("/artifacts");
        onClose();
      },
    });
  }

  if (!mounted || !m) return null;

  return (
    <div
      ref={ref}
      role="menu"
      data-anim="pop"
      data-state={state}
      style={{ left: pos.x, top: pos.y, ["--anim-origin"]: "top left" } as CSSProperties}
      className="fixed z-50 w-44 rounded-lg border border-hairline bg-canvas p-1.5 shadow-float"
    >
      <button
        type="button"
        role="menuitem"
        onClick={onDelete}
        disabled={deleteArtifact.isPending}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-red-600 transition-colors hover:bg-red-50 disabled:opacity-60"
      >
        <svg viewBox="0 0 16 16" aria-hidden className="size-3.5">
          <path
            d="M3 4.5h10M6.5 4.5V3.5a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1M5 4.5l.5 8a1 1 0 0 0 1 .9h3a1 1 0 0 0 1-.9l.5-8"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {deleteArtifact.isPending ? "Deleting…" : "Delete"}
      </button>
    </div>
  );
}
