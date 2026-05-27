"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { ButtonLink, Card, EmptyState, PageHeader, Spinner, StatusBadge, TypeBadge } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useArtifacts } from "@/lib/queries";
import {
  ARTIFACT_TYPE_LABEL,
  ARTIFACT_TYPE_ORDER,
  type ArtifactStatus,
  type ArtifactType,
} from "@/lib/types";

function ArtifactsBrowse() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [type, setType] = useState<ArtifactType | "">("");
  const [status, setStatus] = useState<ArtifactStatus | "">("");

  const { data: artifacts = [], isLoading, isError } = useArtifacts();

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return artifacts
      .filter((a) => (type ? a.type === type : true))
      .filter((a) => (status ? a.status === status : true))
      .filter((a) =>
        needle ? `${a.title} ${a.content}`.toLowerCase().includes(needle) : true,
      );
  }, [artifacts, q, type, status]);

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      <PageHeader
        title="Artifacts"
        description="Browse the connected project memory."
        actions={<ButtonLink href="/artifacts/new">+ Create</ButtonLink>}
      />

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by text…"
          className="w-56 rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value as ArtifactType | "")}
          className="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        >
          <option value="">All types</option>
          {ARTIFACT_TYPE_ORDER.map((t) => (
            <option key={t} value={t}>
              {ARTIFACT_TYPE_LABEL[t]}
            </option>
          ))}
        </select>
        <input
          value={status}
          onChange={(e) => setStatus(e.target.value as ArtifactStatus | "")}
          placeholder="status…"
          list="status-options"
          className="w-32 rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <datalist id="status-options">
          {["draft", "reviewed", "approved", "changed", "active", "archived", "proposed", "in_review", "rejected", "applied"].map(
            (s) => (
              <option key={s} value={s} />
            ),
          )}
        </datalist>
        <span className="text-xs text-neutral-400">{filtered.length} shown</span>
      </div>

      {isLoading && <Spinner label="Loading artifacts…" />}
      {isError && <p className="text-sm text-red-500">Backend offline — start the API server.</p>}

      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyState
          title="Nothing matches"
          hint="Adjust the filters, formalize a description, or create an artifact."
        />
      )}

      {filtered.length > 0 && (
        <Card className="divide-y divide-neutral-100 overflow-hidden dark:divide-neutral-800">
          {filtered.map((a) => (
            <Link
              key={a.id}
              href={`/artifacts/${a.id}`}
              className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
            >
              <TypeBadge type={a.type} />
              <span className="flex-1 truncate text-sm font-medium">{a.title}</span>
              <span className="text-xs text-neutral-400">v{a.current_version}</span>
              <StatusBadge status={a.status} />
              <span className="hidden text-xs text-neutral-400 md:inline">
                {formatDateTime(a.updated_at)}
              </span>
            </Link>
          ))}
        </Card>
      )}
    </div>
  );
}

export default function ArtifactsPage() {
  return (
    <Suspense fallback={<div className="p-6"><Spinner /></div>}>
      <ArtifactsBrowse />
    </Suspense>
  );
}
