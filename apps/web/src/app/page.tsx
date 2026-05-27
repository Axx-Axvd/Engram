"use client";

import Link from "next/link";

import { ButtonLink, Card, EmptyState, PageHeader, Spinner, StatusBadge, TypeBadge } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useArtifacts } from "@/lib/queries";
import { ARTIFACT_TYPE_COLOR, ARTIFACT_TYPE_LABEL, ARTIFACT_TYPE_ORDER } from "@/lib/types";

export default function OverviewPage() {
  const { data: artifacts = [], isLoading, isError } = useArtifacts();

  const recent = [...artifacts]
    .sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))
    .slice(0, 8);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader
        title="Overview"
        description="Project memory at a glance — typed, versioned, connected artifacts."
        actions={
          <>
            <ButtonLink href="/formalize" variant="secondary">
              Formalize
            </ButtonLink>
            <ButtonLink href="/artifacts/new">+ Create</ButtonLink>
          </>
        }
      />

      {isLoading && <Spinner label="Loading workspace…" />}
      {isError && <p className="text-sm text-red-500">Backend offline — start the API server.</p>}

      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Card className="p-4">
              <p className="text-xs text-neutral-500">Documents</p>
              <p className="mt-1 text-2xl font-semibold">{artifacts.length}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-neutral-500">Items</p>
              <p className="mt-1 text-2xl font-semibold">
                {artifacts.reduce((n, a) => n + (a.items?.length ?? 0), 0)}
              </p>
            </Card>
            {ARTIFACT_TYPE_ORDER.map((type) => (
              <Card key={type} className="p-4">
                <p className="flex items-center gap-1.5 text-xs text-neutral-500">
                  <span
                    className="size-2 rounded-full"
                    style={{ background: ARTIFACT_TYPE_COLOR[type] }}
                  />
                  {ARTIFACT_TYPE_LABEL[type]}
                </p>
                <p className="mt-1 text-2xl font-semibold">
                  {artifacts.filter((a) => a.type === type).length}
                </p>
              </Card>
            ))}
          </div>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-neutral-600 dark:text-neutral-300">
              Recently updated
            </h2>
            {recent.length === 0 ? (
              <EmptyState
                title="No artifacts yet"
                hint="Formalize a project description, or create an artifact by hand."
                action={<ButtonLink href="/formalize">Formalize a description</ButtonLink>}
              />
            ) : (
              <Card className="divide-y divide-neutral-100 dark:divide-neutral-800">
                {recent.map((a) => (
                  <Link
                    key={a.id}
                    href={`/artifacts/${a.id}`}
                    className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
                  >
                    <TypeBadge type={a.type} />
                    <span className="flex-1 truncate text-sm font-medium">{a.title}</span>
                    <StatusBadge status={a.status} />
                    <span className="hidden text-xs text-neutral-400 sm:inline">
                      {formatDateTime(a.updated_at)}
                    </span>
                  </Link>
                ))}
              </Card>
            )}
          </section>
        </>
      )}
    </div>
  );
}
