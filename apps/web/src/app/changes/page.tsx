"use client";

import { ButtonLink, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useProject } from "@/lib/project-context";
import { useChangeSets } from "@/lib/queries";

export default function ChangesPage() {
  const { projectId, project } = useProject();
  const changes = useChangeSets(projectId);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader
        title="Changes"
        description={`Actual upstream commits imported for ${project?.name ?? "the selected project"}, with exact before/after item versions.`}
        actions={<ButtonLink href="/sources">Import a commit</ButtonLink>}
      />

      {changes.isLoading ? (
        <Spinner label="Loading changes…" />
      ) : changes.data?.length ? (
        <div className="space-y-3">
          {changes.data.map((change) => (
            <Card key={change.id} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary-deep">
                      {change.status}
                    </span>
                    <span className="font-mono text-xs text-ink-mute">
                      {change.external_id.slice(0, 12)}
                    </span>
                  </div>
                  <h2 className="mt-2 font-medium text-ink">
                    {change.summary.split("\n")[0] || "Imported change"}
                  </h2>
                  <p className="mt-1 text-xs text-ink-mute">
                    {formatDateTime(change.created_at)} · {change.items?.length ?? 0} versioned elements
                    {change.analysis_id ? " · linked to an approved analysis" : " · no analysis link"}
                  </p>
                </div>
                {change.external_url && (
                  <a
                    href={change.external_url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-sm font-medium text-primary-deep hover:underline"
                  >
                    Open commit ↗
                  </a>
                )}
              </div>

              <div className="mt-4 overflow-hidden rounded-md border border-hairline">
                <div className="grid grid-cols-[100px_1fr_1fr] bg-canvas-soft px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                  <span>Change</span>
                  <span>Before version</span>
                  <span>After version</span>
                </div>
                {(change.items ?? []).map((item) => (
                  <div
                    key={item.id}
                    className="grid grid-cols-[100px_1fr_1fr] border-t border-hairline px-3 py-2 text-xs text-ink-mute"
                  >
                    <span>{item.change_kind}</span>
                    <span className="truncate font-mono">{item.before_version_id ?? "—"}</span>
                    <span className="truncate font-mono text-ink">{item.after_version_id ?? "—"}</span>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No actual changes imported"
          hint="Import a fixed GitHub commit. If it implements an approved analysis, select that analysis during sync to preserve the causal link."
          action={<ButtonLink href="/sources">Go to sources</ButtonLink>}
        />
      )}
    </div>
  );
}
