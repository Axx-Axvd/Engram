"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useHealth } from "@/lib/queries";

export function Topbar() {
  const router = useRouter();
  const health = useHealth();
  const [q, setQ] = useState("");

  const status = health.isLoading
    ? { dot: "bg-amber-400", text: "connecting" }
    : health.isSuccess
      ? { dot: "bg-primary", text: "backend connected" }
      : { dot: "bg-red-500", text: "backend offline" };

  return (
    <header className="flex items-center gap-4 border-b border-hairline bg-canvas/80 px-5 py-3 backdrop-blur">
      <Link href="/" className="flex items-baseline gap-2">
        <span className="flex items-center gap-1.5 text-lg font-medium tracking-tight text-ink">
          <span className="size-2 translate-y-px rounded-full bg-primary" />
          Engram
        </span>
        <span className="hidden text-xs text-ink-faint sm:inline">project memory</span>
      </Link>

      <form
        className="flex-1"
        onSubmit={(e) => {
          e.preventDefault();
          router.push(q.trim() ? `/artifacts?q=${encodeURIComponent(q.trim())}` : "/artifacts");
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search artifacts…"
          className="w-full max-w-md rounded-md border border-hairline-strong bg-canvas px-3 py-1.5 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </form>

      <Link
        href="/artifacts/new"
        className="inline-flex min-h-9 items-center gap-1 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-on-primary transition-colors hover:bg-primary-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
      >
        + Create
      </Link>

      <span className="inline-flex items-center gap-2 text-xs text-ink-mute">
        <span className={`size-2 rounded-full ${status.dot}`} />
        <span className="hidden md:inline">{status.text}</span>
      </span>
    </header>
  );
}
