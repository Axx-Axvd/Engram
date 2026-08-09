"use client";

import { useState } from "react";

import { Button, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useProject } from "@/lib/project-context";
import {
  useCreateGitHubSource,
  useImpactAnalyses,
  useSourceRevisions,
  useSources,
  useSyncSource,
} from "@/lib/queries";
import type { ImpactAnalysis, Source } from "@/lib/types";

export default function SourcesPage() {
  const { projectId, project } = useProject();
  const sources = useSources(projectId);
  const create = useCreateGitHubSource(projectId);
  const analyses = useImpactAnalyses(projectId);
  const [repository, setRepository] = useState("");
  const [ref, setRef] = useState("main");

  function connect() {
    if (!repository.trim()) return;
    create.mutate(
      { repository: repository.trim(), ref: ref.trim() || "main" },
      { onSuccess: () => setRepository("") },
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader
        title="Sources"
        description={`Immutable upstream revisions for ${project?.name ?? "the selected project"}. GitHub access is strictly read-only.`}
      />

      <Card className="p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <label className="flex flex-1 flex-col gap-1.5 text-xs font-medium text-ink-mute">
            GitHub repository
            <input
              value={repository}
              onChange={(event) => setRepository(event.target.value)}
              placeholder="owner/repository"
              className="rounded-md border border-hairline-strong px-3 py-2 text-sm font-normal text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <label className="flex w-40 flex-col gap-1.5 text-xs font-medium text-ink-mute">
            Initial ref
            <input
              value={ref}
              onChange={(event) => setRef(event.target.value)}
              className="rounded-md border border-hairline-strong px-3 py-2 text-sm font-normal text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <Button onClick={connect} disabled={!projectId || !repository.trim() || create.isPending}>
            {create.isPending ? "Connecting…" : "Connect GitHub"}
          </Button>
        </div>
        <p className="mt-3 text-xs text-ink-faint">
          Private repositories use the server-side ENGRAM_GITHUB_TOKEN. Credentials are never sent
          to the browser or stored in source configuration.
        </p>
        {create.isError && <p className="mt-2 text-xs text-red-600">Could not connect this source.</p>}
      </Card>

      {sources.isLoading ? (
        <Spinner label="Loading sources…" />
      ) : sources.data?.length ? (
        <div className="space-y-3">
          {sources.data.map((source) => (
            <SourceCard
              key={source.id}
              source={source}
              projectId={projectId}
              analyses={analyses.data ?? []}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No sources connected"
          hint="Connect one GitHub repository, then import a fixed commit SHA before running impact analysis."
        />
      )}
    </div>
  );
}

function SourceCard({
  source,
  projectId,
  analyses,
}: {
  source: Source;
  projectId: string | null;
  analyses: ImpactAnalysis[];
}) {
  const revisions = useSourceRevisions(projectId, source.id);
  const sync = useSyncSource(projectId);
  const configuredRef = String(source.configuration.ref ?? "main");
  const [ref, setRef] = useState(configuredRef);
  const [analysisId, setAnalysisId] = useState("");
  const latest = revisions.data?.[0];
  const isGitHub = source.kind === "github";

  return (
    <Card className="p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-canvas-soft px-2 py-0.5 text-xs font-medium text-ink-mute ring-1 ring-inset ring-hairline">
              {source.kind}
            </span>
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="truncate font-medium text-ink hover:text-primary-deep"
              >
                {source.name}
              </a>
            ) : (
              <span className="font-medium text-ink">{source.name}</span>
            )}
          </div>
          {latest ? (
            <p className="mt-2 text-xs text-ink-mute">
              Latest snapshot <span className="font-mono text-ink">{latest.revision.slice(0, 12)}</span>
              {" · "}{formatDateTime(latest.captured_at)}
            </p>
          ) : (
            <p className="mt-2 text-xs text-ink-mute">Connected, not imported yet.</p>
          )}
        </div>
        {isGitHub && (
          <>
            <input
              value={ref}
              onChange={(event) => setRef(event.target.value)}
              aria-label="Git ref or commit SHA"
              className="w-52 rounded-md border border-hairline-strong px-3 py-2 font-mono text-xs text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <Button
              onClick={() =>
                sync.mutate({ sourceId: source.id, ref, analysisId: analysisId || undefined })
              }
              disabled={sync.isPending || !ref.trim()}
            >
              {sync.isPending ? "Importing…" : "Import revision"}
            </Button>
          </>
        )}
      </div>
      {isGitHub ? (
        <label className="mt-3 flex max-w-xl flex-col gap-1.5 text-xs font-medium text-ink-mute">
        Confirmed analysis for this actual change (optional)
        <select
          value={analysisId}
          onChange={(event) => setAnalysisId(event.target.value)}
          className="rounded-md border border-hairline-strong bg-canvas px-3 py-2 font-normal text-ink outline-none focus:border-primary"
        >
          <option value="">No linked analysis</option>
          {analyses
            ?.filter((analysis) => analysis.status === "approved")
            .map((analysis) => (
              <option key={analysis.id} value={analysis.id}>
                {analysis.request_text}
              </option>
            ))}
        </select>
        </label>
      ) : (
        <p className="mt-3 text-xs text-ink-faint">
          This internal provenance source is maintained automatically for manual and migrated input.
        </p>
      )}
      {sync.data && (
        <p className="mt-3 rounded-md bg-primary/10 p-3 text-xs text-ink">
          Snapshot {sync.data.revision.revision.slice(0, 12)}: {sync.data.imported_items} new,
          {" "}{sync.data.updated_items} updated, {sync.data.deleted_items} deleted, {sync.data.stale_links}
          {" "}links marked stale.
        </p>
      )}
      {sync.isError && (
        <p className="mt-3 text-xs text-red-600">
          Import failed. Check the ref, repository access and API logs; no partial revision was committed.
        </p>
      )}
    </Card>
  );
}
