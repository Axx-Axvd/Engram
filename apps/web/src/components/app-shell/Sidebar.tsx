"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const PRIMARY = [
  { href: "/", label: "Projects", exact: true },
  { href: "/sources", label: "Sources", exact: false },
  { href: "/changes", label: "Changes", exact: false },
  { href: "/impact-analyses", label: "Impact analyses", exact: false },
  { href: "/context-packages", label: "Context packages", exact: false },
];

const DIAGNOSTICS = [
  { href: "/artifacts", label: "Document containers" },
  { href: "/graph", label: "Graph explorer" },
  { href: "/consistency", label: "Consistency" },
  { href: "/formalize", label: "Prototype formalizer" },
];

function active(pathname: string, href: string, exact = false) {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-64 shrink-0 flex-col overflow-y-auto border-r border-hairline bg-canvas-soft px-3 py-4">
      <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
        Change intelligence
      </p>
      <nav className="flex flex-col gap-0.5">
        {PRIMARY.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              active(pathname, item.href, item.exact)
                ? "bg-primary text-on-primary"
                : "text-ink-mute hover:bg-hairline-cool hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="my-4 border-t border-hairline" />
      <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
        Diagnostic tools
      </p>
      <nav className="flex flex-col gap-0.5">
        {DIAGNOSTICS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-3 py-2 text-sm transition-colors ${
              active(pathname, item.href)
                ? "bg-hairline-cool font-medium text-ink"
                : "text-ink-mute hover:bg-hairline-cool hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto rounded-lg border border-hairline bg-canvas p-3 text-xs text-ink-mute">
        Engram reads upstream sources and explains change impact. It never applies model suggestions
        automatically.
      </div>
    </aside>
  );
}
