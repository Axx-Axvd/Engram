"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Button, ButtonLink, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useProject } from "@/lib/project-context";
import {
  useBuildContextPackage,
  useCreateImpactAnalysis,
  useImpactAnalyses,
  useProjectItems,
  useReviewCandidate,
} from "@/lib/queries";

const SAMPLE = "Allow external guests to receive an email invitation and join a shared task list.";

function renderEvidence(value: unknown) {
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export default function ImpactAnalysesPage() {
  const { projectId, project } = useProject();
  const analyses = useImpactAnalyses(projectId);
  const items = useProjectItems(projectId);
  const create = useCreateImpactAnalysis(projectId);
  const build = useBuildContextPackage(projectId);
  const [query, setQuery] = useState(SAMPLE);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tokenBudget, setTokenBudget] = useState(4000);

  const effectiveSelectedId = selectedId ?? analyses.data?.[0]?.id ?? null;
  const selected =
    analyses.data?.find((analysis) => analysis.id === effectiveSelectedId) ?? null;
  const review = useReviewCandidate(projectId, effectiveSelectedId);
  const itemById = useMemo(
    () => new Map((items.data ?? []).map((item) => [item.id, item])),
    [items.data],
  );
  const candidates = selected?.candidates ?? [];
  const approved = candidates.filter((candidate) => candidate.decision === "approved").length;

  function runAnalysis() {
    if (!query.trim()) return;
    create.mutate(query.trim(), { onSuccess: (analysis) => setSelectedId(analysis.id) });
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <PageHeader
        title="Impact analyses"
        description={`Evidence-backed, non-mutating change analysis for ${project?.name ?? "the selected project"}. Every candidate requires review.`}
      />

      <Card className="p-5">
        <label className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Proposed change
        </label>
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={3}
          className="mt-2 w-full resize-y rounded-md border border-hairline-strong bg-canvas p-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        <div className="mt-3 flex items-center justify-between gap-4">
          <p className="text-xs text-ink-mute">
            The model receives versioned items, source locators, confirmed graph paths and a hard
            context budget. Its output cannot update active versions.
          </p>
          <Button onClick={runAnalysis} disabled={!projectId || !query.trim() || create.isPending}>
            {create.isPending ? "Analyzing…" : "Analyze impact"}
          </Button>
        </div>
        {create.isError && (
          <p className="mt-3 text-xs text-red-600">
            Analysis was rejected. Invalid model output is discarded as one transaction.
          </p>
        )}
      </Card>

      {analyses.isLoading ? (
        <Spinner label="Loading analyses…" />
      ) : analyses.data?.length ? (
        <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="space-y-2">
            {analyses.data.map((analysis) => (
              <button
                type="button"
                key={analysis.id}
                onClick={() => setSelectedId(analysis.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                analysis.id === effectiveSelectedId
                    ? "border-primary bg-primary/5"
                    : "border-hairline bg-canvas hover:border-hairline-strong"
                }`}
              >
                <span className="line-clamp-2 text-sm font-medium text-ink">
                  {analysis.request_text}
                </span>
                <span className="mt-2 flex items-center justify-between text-xs text-ink-faint">
                  <span>{analysis.status.replace("_", " ")}</span>
                  <span>{formatDateTime(analysis.created_at)}</span>
                </span>
              </button>
            ))}
          </aside>

          {selected && (
            <section className="min-w-0 space-y-4">
              <Card className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-canvas-soft px-2 py-0.5 text-xs font-medium text-ink-mute ring-1 ring-inset ring-hairline">
                        {selected.status.replace("_", " ")}
                      </span>
                      <span className="text-xs text-ink-faint">
                        {selected.model_provider} · {selected.retrieval_mode} retrieval · {selected.algorithm_version}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-ink">{selected.summary}</p>
                  </div>
                  <div className="flex items-end gap-2">
                    <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
                      Token budget
                      <input
                        type="number"
                        min={128}
                        max={100000}
                        value={tokenBudget}
                        onChange={(event) => setTokenBudget(Number(event.target.value))}
                        className="w-28 rounded-md border border-hairline-strong px-2 py-1.5 text-xs font-normal text-ink outline-none focus:border-primary"
                      />
                    </label>
                    <Button
                      onClick={() =>
                        build.mutate({ analysisId: selected.id, tokenBudget })
                      }
                      disabled={!approved || build.isPending || tokenBudget < 128}
                    >
                      {build.isPending ? "Building…" : `Build package (${approved})`}
                    </Button>
                  </div>
                </div>
                {build.data && (
                  <p className="mt-3 rounded-md bg-primary/10 p-3 text-xs text-ink">
                    Context Package created with {build.data.items.length} items and {build.data.token_estimate}
                    /{build.data.token_budget} estimated tokens. {" "}
                    <Link href="/context-packages" className="font-medium text-primary-deep hover:underline">
                      Open package →
                    </Link>
                  </p>
                )}
                {build.isError && (
                  <p className="mt-3 text-xs text-red-600">
                    Approve at least one item that fits the requested hard budget.
                  </p>
                )}
              </Card>

              <div className="overflow-x-auto rounded-lg border border-hairline bg-canvas shadow-card">
                <table className="w-full min-w-[980px] border-collapse text-left text-xs">
                  <thead className="bg-canvas-soft text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                    <tr>
                      <th className="px-3 py-2.5">Element</th>
                      <th className="px-3 py-2.5">Impact</th>
                      <th className="px-3 py-2.5">Evidence and rationale</th>
                      <th className="px-3 py-2.5">Selection</th>
                      <th className="px-3 py-2.5">Review</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline">
                    {candidates.map((candidate) => {
                      const item = itemById.get(candidate.item_id);
                      const graphPath = candidate.selection_reason.graph_path;
                      return (
                        <tr key={candidate.id} className="align-top">
                          <td className="max-w-56 px-3 py-3">
                            <p className="font-medium text-ink">{item?.title ?? candidate.item_id}</p>
                            <p className="mt-1 font-mono text-[10px] text-ink-faint">
                              {item?.type ?? "item"} · {candidate.item_version_id.slice(0, 8)}
                            </p>
                          </td>
                          <td className="px-3 py-3">
                            <span className="font-medium text-ink">{candidate.impact_type}</span>
                            <span className="mt-1 block text-ink-mute">
                              {Math.round(candidate.confidence * 100)}% confidence
                            </span>
                            {candidate.proposed_action && (
                              <p className="mt-2 max-w-48 text-ink-mute">{candidate.proposed_action}</p>
                            )}
                          </td>
                          <td className="max-w-sm px-3 py-3 text-ink-mute">
                            <p>{candidate.rationale}</p>
                            <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px] text-ink-faint">
                              {candidate.evidence.map((evidence, index) => (
                                <li key={index}>{renderEvidence(evidence)}</li>
                              ))}
                            </ul>
                          </td>
                          <td className="max-w-56 px-3 py-3 text-[11px] text-ink-mute">
                            <p>score {String(candidate.selection_reason.score ?? "—")}</p>
                            <p>tokens {String(candidate.selection_reason.token_estimate ?? "—")}</p>
                            {Array.isArray(graphPath) && graphPath.length > 0 ? (
                              <p className="mt-1 break-words">path {graphPath.map(renderEvidence).join(" → ")}</p>
                            ) : (
                              <p className="mt-1 text-ink-faint">direct retrieval candidate</p>
                            )}
                          </td>
                          <td className="px-3 py-3">
                            {candidate.decision === "pending" ? (
                              <div className="flex gap-2">
                                <Button
                                  className="px-2.5 py-1.5 text-xs"
                                  onClick={() =>
                                    review.mutate({ candidateId: candidate.id, decision: "approved" })
                                  }
                                  disabled={review.isPending}
                                >
                                  Approve
                                </Button>
                                <Button
                                  className="px-2.5 py-1.5 text-xs"
                                  variant="secondary"
                                  onClick={() =>
                                    review.mutate({ candidateId: candidate.id, decision: "rejected" })
                                  }
                                  disabled={review.isPending}
                                >
                                  Reject
                                </Button>
                              </div>
                            ) : (
                              <span
                                className={`font-medium ${
                                  candidate.decision === "approved" ? "text-primary-deep" : "text-red-600"
                                }`}
                              >
                                {candidate.decision}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      ) : (
        <EmptyState
          title="No impact analyses"
          hint="Describe a proposed change above. Connect GitHub first when the analysis must use repository-backed evidence."
          action={<ButtonLink href="/sources">Open sources</ButtonLink>}
        />
      )}
    </div>
  );
}
