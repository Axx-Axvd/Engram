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
      ? { dot: "bg-emerald-500", text: "backend connected" }
      : { dot: "bg-red-500", text: "backend offline" };

  return (
    <header className="flex items-center gap-4 border-b border-neutral-200 bg-white/80 px-5 py-3 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/80">
      <Link href="/" className="flex items-baseline gap-2">
        <span className="text-lg font-semibold tracking-tight">Engram</span>
        <span className="hidden text-xs text-neutral-400 sm:inline">project memory</span>
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
          className="w-full max-w-md rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
        />
      </form>

      <Link
        href="/artifacts/new"
        className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
      >
        + Create
      </Link>

      <span className="inline-flex items-center gap-2 text-xs text-neutral-500">
        <span className={`size-2 rounded-full ${status.dot}`} />
        <span className="hidden md:inline">{status.text}</span>
      </span>
    </header>
  );
}
