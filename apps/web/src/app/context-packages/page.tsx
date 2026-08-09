"use client";

import { useState } from "react";

import { Button, ButtonLink, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useProject } from "@/lib/project-context";
import { useContextPackages } from "@/lib/queries";

export default function ContextPackagesPage() {
  const { projectId, project } = useProject();
  const packages = useContextPackages(projectId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const effectiveSelectedId = selectedId ?? packages.data?.[0]?.id ?? null;
  const selected = packages.data?.find((value) => value.id === effectiveSelectedId) ?? null;
  const utilization = selected
    ? Math.min(100, Math.round((selected.token_estimate / selected.token_budget) * 100))
    : 0;

  async function copyPackage() {
    if (!selected) return;
    await navigator.clipboard.writeText(JSON.stringify(selected, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <PageHeader
        title="Context packages"
        description={`Immutable, explainable knowledge snapshots for agents working on ${project?.name ?? "the selected project"}.`}
        actions={<ButtonLink href="/impact-analyses">Run analysis</ButtonLink>}
      />

      {packages.isLoading ? (
        <Spinner label="Loading context packages…" />
      ) : packages.data?.length ? (
        <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="space-y-2">
            {packages.data.map((value) => (
              <button
                type="button"
                key={value.id}
                onClick={() => setSelectedId(value.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  value.id === effectiveSelectedId
                    ? "border-primary bg-primary/5"
                    : "border-hairline bg-canvas hover:border-hairline-strong"
                }`}
              >
                <span className="block text-sm font-medium text-ink">
                  {value.items.length} knowledge elements
                </span>
                <span className="mt-1 block text-xs text-ink-mute">
                  {value.token_estimate}/{value.token_budget} tokens
                </span>
                <span className="mt-2 block font-mono text-[10px] text-ink-faint">
                  {value.id.slice(0, 12)} · {formatDateTime(value.created_at)}
                </span>
              </button>
            ))}
          </aside>

          {selected && (
            <section className="min-w-0 space-y-4">
              <Card className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-ink">Hard token budget</p>
                    <p className="mt-1 text-xs text-ink-mute">
                      {selected.token_estimate} of {selected.token_budget} estimated tokens used ({utilization}%).
                    </p>
                  </div>
                  <Button variant="secondary" onClick={copyPackage}>
                    {copied ? "Copied" : "Copy JSON"}
                  </Button>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-hairline-cool">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${utilization}%` }} />
                </div>
                <p className="mt-3 font-mono text-[10px] text-ink-faint">
                  analysis {selected.analysis_id} · package {selected.id}
                </p>
              </Card>

              <div className="space-y-3">
                {selected.items.map((entry) => (
                  <Card key={entry.version.id} className="p-5">
                    <div className="flex items-start gap-4">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary-deep">
                        {entry.rank}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="font-medium text-ink">{entry.version.title}</h2>
                          <span className="rounded-full bg-canvas-soft px-2 py-0.5 text-[11px] text-ink-mute ring-1 ring-inset ring-hairline">
                            {entry.item.type} · v{entry.version.version}
                          </span>
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-mute">
                          {entry.version.text}
                        </p>
                        <div className="mt-4 grid gap-3 border-t border-hairline pt-3 text-xs text-ink-mute md:grid-cols-3">
                          <div>
                            <span className="block text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                              Retrieval score
                            </span>
                            {entry.score.toFixed(3)}
                          </div>
                          <div>
                            <span className="block text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                              Estimated tokens
                            </span>
                            {entry.token_estimate}
                          </div>
                          <div>
                            <span className="block text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                              Fixed source locator
                            </span>
                            {entry.source_locator ? (
                              <span className="block break-words font-mono text-[10px]">
                                {entry.source_locator.url ? (
                                  <a
                                    href={entry.source_locator.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-primary-deep hover:underline"
                                  >
                                    {entry.source_locator.path ?? entry.source_locator.external_id ?? "source"}
                                  </a>
                                ) : (
                                  entry.source_locator.path ?? entry.source_locator.external_id ?? "manual input"
                                )}
                                {entry.source_locator.start_line
                                  ? `:${entry.source_locator.start_line}${
                                      entry.source_locator.end_line
                                        ? `-${entry.source_locator.end_line}`
                                        : ""
                                    }`
                                  : ""}
                                <span className="mt-1 block text-ink-faint">
                                  {entry.source_locator.content_hash?.slice(0, 16)}
                                </span>
                              </span>
                            ) : (
                              <span className="text-red-600">missing</span>
                            )}
                          </div>
                        </div>
                        <details className="mt-3 text-xs text-ink-mute">
                          <summary className="cursor-pointer font-medium text-ink">Why this item?</summary>
                          <pre className="mt-2 overflow-x-auto rounded-md bg-canvas-soft p-3 text-[11px]">
                            {JSON.stringify({ reason: entry.reason, graph_path: entry.graph_path }, null, 2)}
                          </pre>
                        </details>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </section>
          )}
        </div>
      ) : (
        <EmptyState
          title="No Context Packages"
          hint="Review impact candidates first. Only approved, version-pinned elements can enter a package, and the final result must fit its hard token budget."
          action={<ButtonLink href="/impact-analyses">Review analyses</ButtonLink>}
        />
      )}
    </div>
  );
}
